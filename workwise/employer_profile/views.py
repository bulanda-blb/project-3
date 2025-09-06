from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import json, re, datetime
from datetime import datetime, date
from decimal import Decimal
from .models import JobPost, CompanyProfile
from authentication.models import Employer, Candidate
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Min
from .utils.ranking    import rank_applications
from candidate_profile.models import JobApplication
from django.contrib   import messages
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from dateutil.relativedelta import relativedelta
from .models import EmployerPremium


def dashboard(request):
    # 1) Auth & fetch employer
    eid = request.session.get('employer_id')
    if not eid:
        return redirect('authentication:login')
    employer = get_object_or_404(Employer, employer_id=eid)

    # 2) Summary cards
    total_posts    = employer.job_posts.count()
    active_posts   = employer.job_posts.filter(is_active=True, admin_review=False).count()
    pending_posts  = employer.job_posts.filter(admin_review=True).count()
    closed_posts   = employer.job_posts.filter(is_active=False).count()

    all_apps = JobApplication.objects.filter(job__employer=employer)
    total_apps      = all_apps.count()
    interviews_sch  = all_apps.filter(status='interview').count()
    offers_ext      = all_apps.filter(status='offered').count()

    # 3) Status distribution (pie/donut)
    statuses     = ['applied','reviewing','interview','offered','rejected']
    status_labels = ['Applied','Reviewing','Interview','Offered','Rejected']
    status_data   = [ all_apps.filter(status=s).count() for s in statuses ]

    # 4) Applications over last 6 months (line chart)
    now = timezone.now()
    activity_labels = []
    activity_data   = []
    for i in reversed(range(6)):
        m = now - relativedelta(months=i)
        label = m.strftime('%b %Y')
        cnt = all_apps.filter(
            applied_at__year=m.year,
            applied_at__month=m.month
        ).count()
        activity_labels.append(label)
        activity_data.append(cnt)

    # 5) Top 5 jobs by application count (horizontal bar)
    top_jobs_qs = (
        employer.job_posts
                .annotate(app_count=Count('applications'))
                .order_by('-app_count')[:5]
    )
    top_jobs_labels = [ f"{jp.title}" for jp in top_jobs_qs ]
    top_jobs_data   = [ jp.app_count     for jp in top_jobs_qs ]

    # 6) Upcoming interviews (next 5)
    upcoming = all_apps.filter(
        status='interview',
        interview_at__gte=now
    ).select_related('candidate','job') \
     .order_by('interview_at')[:5]

    # 7) Company Profile completeness (4 checks)
    try:
        cp = employer.company_profile
    except CompanyProfile.DoesNotExist:
        cp = None

    criteria = [
        ('Description',      bool(cp and cp.description)),
        ('Logo Uploaded',    bool(cp and cp.logo)),
        ('Website Set',      bool(cp and cp.website)),
        ('Phone Number',     bool(cp and cp.phone_number)),
    ]
    weight = 100 / len(criteria)
    profile_segments = [
        {'name': name, 'done': done, 'width': weight}
        for name, done in criteria
    ]

    # overall percentage (for validation / button toggle)
    completeness = int(
        sum(1 for seg in profile_segments if seg['done']) 
        / len(profile_segments) * 100
    )

    return render(request, 'employer_profile/dashboard.html', {
        'total_posts':     total_posts,
        'active_posts':    active_posts,
        'pending_posts':   pending_posts,
        'closed_posts':    closed_posts,
        'total_apps':      total_apps,
        'interviews_sch':  interviews_sch,
        'offers_ext':      offers_ext,
        'status_labels':   json.dumps(status_labels),
        'status_data':     json.dumps(status_data),
        'activity_labels': json.dumps(activity_labels),
        'activity_data':   json.dumps(activity_data),
        'top_jobs_labels': json.dumps(top_jobs_labels),
        'top_jobs_data':   json.dumps(top_jobs_data),
        'upcoming':        upcoming,
        'profile_segments':  profile_segments,
        'profile_completeness': completeness,
        'employer':        employer,
    })




INDUSTRIES = [
  'information_technology','management','business','finance','healthcare','education',
  'manufacturing','construction','retail','hospitality','telecommunication',
  'transportation','legal','human_resources','marketing_advertising','media_entertainment',
  'research_development','non_profit','government','agriculture','energy_utilities',
  'pharmaceutical','aerospace','automotive','tourism','food_beverage','beauty_wellness',
  'sports_recreation','arts_culture','environmental','security','consulting'
]

DEPARTMENTS = {
  'information_technology': ['software_development','devops','it_support','network_engineering','data_science'],
  'management': ['project_management','operations','product_management','strategy','risk_management'],
  'business': ['business_analysis','sales','business_development','customer_success'],
  'finance': ['accounting','audit','treasury','investment_banking','financial_planning'],
  'healthcare': ['nursing','medical_administration','healthcare_it','pharmacy','physiotherapy'],
  'education': ['teaching','curriculum_development','admissions','administration'],
  'manufacturing': ['production','quality_assurance','maintenance','supply_chain_management'],
  'construction': ['site_management','civil_engineering','architecture','safety'],
  'retail': ['store_management','merchandising','inventory_management','customer_service'],
  'hospitality': ['hotel_management','food_beverage','front_desk','housekeeping'],
  'telecommunication': ['network_operations','technical_support','sales','engineering'],
  'transportation': ['logistics','fleet_management','transportation_planning','operations'],
  'legal': ['corporate_law','compliance','contracts','litigation'],
  'human_resources': ['recruitment','learning_development','compensation_benefits','employee_relations'],
  'marketing_advertising': ['digital_marketing','brand_management','market_research','public_relations'],
  'media_entertainment': ['journalism','editing','production','social_media'],
  'research_development': ['lab_research','clinical_trials','product_innovation'],
  'non_profit': ['program_management','fundraising','volunteer_coordination','advocacy'],
  'government': ['policy_development','public_administration','regulatory_affairs'],
  'agriculture': ['crop_science','farm_management','agricultural_technology','quality_control'],
  'energy_utilities': ['oil_gas','renewable_energy','safety_management','procurement'],
  'pharmaceutical': ['r_and_d','regulatory_affairs','quality_control','sales'],
  'aerospace': ['avionics','aircraft_design','maintenance','flight_operations'],
  'automotive': ['automotive_engineering','manufacturing','quality_assurance','sales'],
  'tourism': ['travel_concierge','tour_operations','event_planning','marketing'],
  'food_beverage': ['culinary_arts','quality_control','procurement','sales'],
  'beauty_wellness': ['cosmetology','retail','product_development','marketing'],
  'sports_recreation': ['coaching','operations','sales','event_management'],
  'arts_culture': ['gallery_management','curation','production','education'],
  'environmental': ['environmental_consulting','field_research','policy_development'],
  'security': ['physical_security','cybersecurity','investigations'],
  'consulting': ['strategy_consulting','it_consulting','management_consulting','hr_consulting']
}

WORK_TYPES = ['part_time','full_time','contract','internship']
GENDERS = ['male','female','no_requirement']
EXP_LEVELS = ['intern','junior','mid','senior']
SALARY_TYPES = ['fixed','negotiable']
FREQS = {'hourly','weekly','monthly','quarterly','yearly'}
LOCATION_TYPES = ['remote','onsite','office','hybrid']



def job_create(request):
    emp_id = request.session.get('employer_id')
    if not emp_id:
        return redirect(reverse('authentication:login'))
    try:
        employer = Employer.objects.get(pk=emp_id)
    except Employer.DoesNotExist:
        return redirect(reverse('authentication:login'))
    
        # — PROFILE COMPLETENESS & VERIFICATION CHECK —
    profile = CompanyProfile.objects.filter(employer=employer).first()
    missing = []

    # 1) Required details
    if not profile or not profile.logo:
        missing.append("upload your company logo")
    if not profile or not profile.company_size:
        missing.append("select your company size")
    if not profile or not profile.founded_date:
        missing.append("enter your company’s founded date")
    if not profile or not profile.phone_number:
        missing.append("provide a valid phone number")
    if not profile or not profile.address:
        missing.append("fill in your company address")

    # If any detail is missing, block here
    if missing:
        message = "Please " + ", ".join(missing) + " before you can post a job."
        return render(request, 'employer_profile/job_create_blocked.html', {
            'message': message,
            'profile_url': reverse('employer:profile_manage'),
        })

    # 2) Certificate & verification
    if not employer.is_verified:
        if profile and profile.certificate:
            message = "Your verification is pending. Please wait until your account is verified."
        else:
            message = "Please upload your verification certificate to create a job post."
        return render(request, 'employer_profile/job_create_blocked.html', {
            'message': message,
            'profile_url': reverse('employer:profile_manage'),
        })

    

    premium_obj, _ = EmployerPremium.objects.get_or_create(employer=employer)
    now = timezone.now()
    if not (
            premium_obj.is_subscribed
            and premium_obj.payment_ok
            and premium_obj.subscription_end
            and premium_obj.subscription_end >= now
        ):
        return redirect(reverse('employer:premium'))

    errors = {}
    values = {}

    if request.method == 'POST':
        # 1) Extract & trim all fields
        for field in [
            'contact_email','application_deadline','title','industry','department',
            'work_type','gender_requirement','experience_level',
            'experience_min','experience_max','salary_type',
            'salary_min','salary_max','num_candidates_required','salary_frequency',
            'requirements','preferred_skills','languages','benefits',
            'location_type','full_location_address','description','map_location'
        ]:
            values[field] = request.POST.get(field, '').strip()

        # 2) Validate contact_email
        email = values['contact_email']
        if not email:
            errors['contact_email'] = 'Required.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['contact_email'] = 'Invalid email.'

        # 3) Validate application_deadline
        dl = values['application_deadline']
        if not dl:
            errors['application_deadline'] = 'Required.'
        else:
            try:
                parsed = datetime.strptime(dl, '%Y-%m-%d')
            except ValueError:
                errors['application_deadline'] = 'Invalid date.'
            else:
                if parsed < datetime.today():
                    errors['application_deadline'] = 'Deadline cannot be in the past.'

        # 4) Title
        title = values['title']
        if not title:
            errors['title'] = 'Required.'
        elif len(title) > 200:
            errors['title'] = 'Max 200 characters.'

        # 5) Industry & department
        ind = values['industry']
        if ind not in INDUSTRIES:
            errors['industry'] = 'Select a valid industry.'
        dept = values['department']
        if not dept:
            errors['department'] = 'Required.'
        elif ind in DEPARTMENTS and dept not in DEPARTMENTS[ind]:
            errors['department'] = 'Select a valid department.'

        # 6) Work type & gender
        if values['work_type'] not in WORK_TYPES:
            errors['work_type'] = 'Select a valid work type.'
        if values['gender_requirement'] not in GENDERS:
            errors['gender_requirement'] = 'Select a valid option.'

        # 7) Experience logic
        exp_lvl = values['experience_level']
        if exp_lvl not in EXP_LEVELS:
            errors['experience_level'] = 'Select a valid experience level.'
        else:
            if exp_lvl == 'intern':
                exp_min = exp_max = 0
            else:
                # parse min/max
                try:
                    exp_min = int(values['experience_min'])
                    exp_max = int(values['experience_max'])
                    if exp_min < 0 or exp_max < 0 or exp_min > exp_max:
                        raise ValueError
                except (ValueError, TypeError):
                    errors['experience_min'] = 'Enter valid min ≤ max.'
                    errors['experience_max'] = 'Enter valid min ≤ max.'

        # 8) Salary logic
        sal_type = values['salary_type']
        if sal_type not in SALARY_TYPES:
            errors['salary_type'] = 'Select a valid salary type.'
        else:
            if sal_type == 'fixed':
                sal_min = Decimal('0')
                try:
                    sal_max = Decimal(values['salary_max'])
                    if sal_max < 0: raise ValueError
                except:
                    errors['salary_max'] = 'Enter valid number.'
            else:  # negotiable
                try:
                    sal_min = Decimal(values['salary_min'])
                    sal_max = Decimal(values['salary_max'])
                    if sal_min < 0 or sal_max < 0 or sal_min >= sal_max:
                        raise ValueError
                except:
                    errors['salary_min'] = 'Enter valid number < max.'
                    errors['salary_max'] = 'Enter valid number > min.'

        # 9) Number of candidates
        try:
            num_req = int(values['num_candidates_required'])
            if num_req < 1:
                raise ValueError
        except:
            errors['num_candidates_required'] = 'Enter an integer ≥ 1.'


        freq = values['salary_frequency']
        if freq not in FREQS:
            errors['salary_frequency'] = 'Select a valid frequency.'

        # 10) Comma-separated lists
        for field in ['requirements','preferred_skills','languages','benefits']:
            val = values[field]
            if not val:
                errors[field] = 'Required.'
            elif ',' not in val:
                errors[field] = 'Use comma-separated values.'

        # 11) Location fields
        if values['location_type'] not in LOCATION_TYPES:
            errors['location_type'] = 'Select a valid option.'
        if not values['full_location_address']:
            errors['full_location_address'] = 'Required.'

        # 12) Description ≥50 words
        desc = values['description']
        if not desc:
            errors['description'] = 'Required.'
        elif len(desc.split()) < 50:
            errors['description'] = 'At least 50 words required.'

        loc = values['map_location']
        if not loc:
            errors['map_location'] = 'Location is required.'
        else:
            try:
                data = json.loads(loc)
                lat = float(data.get('lat'))
                lng = float(data.get('lng'))
                if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    raise ValueError
            except Exception:
                errors['map_location'] = 'Invalid location coordinates.'

        # If no errors, save
        if not errors:
            job = JobPost()
            job.employer = employer
            job.contact_email = email
            job.application_deadline = datetime.strptime(dl, '%Y-%m-%d').date()
            job.title = title
            job.industry = ind
            job.department = dept
            job.work_type = values['work_type']
            job.gender_requirement = values['gender_requirement']
            job.experience_level = exp_lvl
            job.experience_min = exp_min
            job.experience_max = exp_max
            job.salary_type = sal_type
            job.salary_frequency = freq
            job.salary_min = sal_min
            job.salary_max = sal_max
            job.num_candidates_required = num_req
            job.requirements = [s.strip() for s in values['requirements'].split(',')]
            job.preferred_skills = [s.strip() for s in values['preferred_skills'].split(',')]
            job.languages = [s.strip() for s in values['languages'].split(',')]
            job.benefits = [s.strip() for s in values['benefits'].split(',')]
            job.location_type = values['location_type']
            job.full_location_address = values['full_location_address']
            job.description = desc
            job.is_active = True
            job.admin_review = False
            job.map_location = {'lat': lat, 'lng': lng}
            job.save()
            return HttpResponse('success')

    # GET or errors: render form with old values
    return render(request, 'employer_profile/job_form.html', {
        'errors': errors,
        'values': values,
    })





def manage_jobs(request):
    emp_id = request.session.get('employer_id')
    if not emp_id:
        return redirect('authentication:login')
    employer = get_object_or_404(Employer, pk=emp_id)

    today = date.today()

    # Annotate each post with a status_rank: 0=active, 1=deactivated, 2=expired
    qs = (
        JobPost.objects
        .filter(employer=employer)
        .annotate(
            status_rank=Case(
                When(is_active=True, application_deadline__gte=today, then=Value(0)),
                When(is_active=False, then=Value(1)),
                When(is_active=True, application_deadline__lt=today, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
                
            ),
            applications_count=Count('applications'),
            
        )
        .order_by('status_rank', '-posted_at')
    )

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    jobs = []
    for job in page_obj:
        if not job.is_active:
            status = 'deactivated'
        elif job.application_deadline < today:
            status = 'expired'
        else:
            status = 'active'
        days_left = (job.application_deadline - today).days
        jobs.append({
            'job_id': job.job_id,
            'title': job.title,
            'posted_at': job.posted_at,
            'posted_at_ts': job.posted_at.timestamp(),
            'application_deadline': job.application_deadline.isoformat(),
            'days_left': days_left,
            'status': status,
            'num_candidates_required': job.num_candidates_required,
            'department': job.department,
            'work_type': job.work_type,
            'applications_count': job.applications_count,
           
        })

    all_jobs = []
    for job in qs:   
        if not job.is_active:
            st = 'deactivated'
        elif job.application_deadline < today:
            st = 'expired'
        else:
            st = 'active'
        days_left = (job.application_deadline - today).days
        all_jobs.append({
            'job_id': job.job_id,
            'title': job.title,
            'posted_at': job.posted_at,
            'posted_at_ts': job.posted_at.timestamp(),
            'application_deadline': job.application_deadline.isoformat(),
            'days_left': days_left,
            'status': st,
            'department': job.department,
            'work_type': job.work_type,
            'num_candidates_required': job.num_candidates_required,
            'applications_count': job.applications_count,
            
        })    

    return render(request, 'employer_profile/manage_jobs.html', {
        'jobs': jobs,
        'page_obj': page_obj,
        'all_jobs_json':   json.dumps(all_jobs, cls=DjangoJSONEncoder),
    })





def edit_job(request, job_id):
    emp_id = request.session.get('employer_id')
    if not emp_id:
        return redirect('authentication:login')

    employer = get_object_or_404(Employer, pk=emp_id)
    job = get_object_or_404(JobPost, job_id=job_id)

    if job.employer != employer:
        return HttpResponseForbidden("You’re not allowed to edit this job.")
    
    errors = {}
    values = {}

    if request.method == 'POST':
        # 1) Extract & trim all fields
        for field in [
            'contact_email','application_deadline','title','industry','department',
            'work_type','gender_requirement','experience_level',
            'experience_min','experience_max','salary_type',
            'salary_min','salary_max','num_candidates_required','salary_frequency',
            'requirements','preferred_skills','languages','benefits',
            'location_type','full_location_address','description','map_location'
        ]:
            values[field] = request.POST.get(field, '').strip()

        # 2) Validate contact_email
        email = values['contact_email']
        if not email:
            errors['contact_email'] = 'Required.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['contact_email'] = 'Invalid email.'

        # 3) Validate application_deadline
        dl = values['application_deadline']
        if not dl:
            errors['application_deadline'] = 'Required.'
        else:
            try:
                parsed = datetime.strptime(dl, '%Y-%m-%d')
            except ValueError:
                errors['application_deadline'] = 'Invalid date.'
            else:
                if parsed < datetime.today():
                    errors['application_deadline'] = 'Deadline cannot be in the past.'

        # 4) Title
        title = values['title']
        if not title:
            errors['title'] = 'Required.'
        elif len(title) > 200:
            errors['title'] = 'Max 200 characters.'

        # 5) Industry & department
        ind = values['industry']
        if ind not in INDUSTRIES:
            errors['industry'] = 'Select a valid industry.'
        dept = values['department']
        if not dept:
            errors['department'] = 'Required.'
        elif ind in DEPARTMENTS and dept not in DEPARTMENTS[ind]:
            errors['department'] = 'Select a valid department.'

        # 6) Work type & gender
        if values['work_type'] not in WORK_TYPES:
            errors['work_type'] = 'Select a valid work type.'
        if values['gender_requirement'] not in GENDERS:
            errors['gender_requirement'] = 'Select a valid option.'

        # 7) Experience logic
        exp_lvl = values['experience_level']
        if exp_lvl not in EXP_LEVELS:
            errors['experience_level'] = 'Select a valid experience level.'
        else:
            if exp_lvl == 'intern':
                exp_min = exp_max = 0
            else:
                # parse min/max
                try:
                    exp_min = int(values['experience_min'])
                    exp_max = int(values['experience_max'])
                    if exp_min < 0 or exp_max < 0 or exp_min > exp_max:
                        raise ValueError
                except (ValueError, TypeError):
                    errors['experience_min'] = 'Enter valid min ≤ max.'
                    errors['experience_max'] = 'Enter valid min ≤ max.'

        # 8) Salary logic
        sal_type = values['salary_type']
        if sal_type not in SALARY_TYPES:
            errors['salary_type'] = 'Select a valid salary type.'
        else:
            if sal_type == 'fixed':
                sal_min = Decimal('0')
                try:
                    sal_max = Decimal(values['salary_max'])
                    if sal_max < 0: raise ValueError
                except:
                    errors['salary_max'] = 'Enter valid number.'
            else:  # negotiable
                try:
                    sal_min = Decimal(values['salary_min'])
                    sal_max = Decimal(values['salary_max'])
                    if sal_min < 0 or sal_max < 0 or sal_min >= sal_max:
                        raise ValueError
                except:
                    errors['salary_min'] = 'Enter valid number < max.'
                    errors['salary_max'] = 'Enter valid number > min.'

        # 9) Number of candidates
        try:
            num_req = int(values['num_candidates_required'])
            if num_req < 1:
                raise ValueError
        except:
            errors['num_candidates_required'] = 'Enter an integer ≥ 1.'


        freq = values['salary_frequency']
        if freq not in FREQS:
            errors['salary_frequency'] = 'Select a valid frequency.'

        # 10) Comma-separated lists
        for field in ['requirements','preferred_skills','languages','benefits']:
            val = values[field]
            if not val:
                errors[field] = 'Required.'
            elif ',' not in val:
                errors[field] = 'Use comma-separated values.'

        # 11) Location fields
        if values['location_type'] not in LOCATION_TYPES:
            errors['location_type'] = 'Select a valid option.'
        if not values['full_location_address']:
            errors['full_location_address'] = 'Required.'

        # 12) Description ≥50 words
        desc = values['description']
        if not desc:
            errors['description'] = 'Required.'
        elif len(desc.split()) < 50:
            errors['description'] = 'At least 50 words required.'

        loc = values['map_location']
        if not loc:
            errors['map_location'] = 'Location is required.'
        else:
            try:
                data = json.loads(loc)
                lat = float(data.get('lat'))
                lng = float(data.get('lng'))
                if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    raise ValueError
            except Exception:
                errors['map_location'] = 'Invalid location coordinates.'

        # If no errors, save changes
        if not errors:
            job.contact_email         = values['contact_email']
            job.application_deadline  = datetime.strptime(values['application_deadline'], '%Y-%m-%d').date()
            job.title                 = values['title']
            job.industry              = values['industry']
            job.department            = values['department']
            job.work_type             = values['work_type']
            job.gender_requirement    = values['gender_requirement']
            job.experience_level      = values['experience_level']
            job.experience_min        = exp_min
            job.experience_max        = exp_max
            job.salary_type           = values['salary_type']
            job.salary_frequency      = values['salary_frequency']
            job.salary_min            = sal_min
            job.salary_max            = sal_max
            job.num_candidates_required = num_req
            job.requirements          = [s.strip() for s in values['requirements'].split(',')]
            job.preferred_skills      = [s.strip() for s in values['preferred_skills'].split(',')]
            job.languages             = [s.strip() for s in values['languages'].split(',')]
            job.benefits              = [s.strip() for s in values['benefits'].split(',')]
            job.location_type         = values['location_type']
            job.full_location_address = values['full_location_address']
            job.map_location          = json.loads(values['map_location'])
            job.description           = values['description']
            job.save()
            return redirect(reverse('employer:manage_jobs'))

    else:
        # Populate values from the existing job
        values = {
            'contact_email': job.contact_email,
            'application_deadline': job.application_deadline.isoformat(),
            'title': job.title,
            'industry': job.industry,
            'department': job.department,
            'work_type': job.work_type,
            'gender_requirement': job.gender_requirement,
            'experience_level': job.experience_level,
            'experience_min': job.experience_min,
            'experience_max': job.experience_max,
            'salary_type': job.salary_type,
            'salary_frequency': job.salary_frequency,
            'salary_min': str(job.salary_min),
            'salary_max': str(job.salary_max),
            'num_candidates_required': job.num_candidates_required,
            'requirements': ', '.join(job.requirements),
            'preferred_skills': ', '.join(job.preferred_skills),
            'languages': ', '.join(job.languages),
            'benefits': ', '.join(job.benefits),
            'location_type': job.location_type,
            'full_location_address': job.full_location_address,
            'map_location': json.dumps(job.map_location),
            'description': job.description,
        }

    return render(request, 'employer_profile/edit_jobs.html', {
        'errors':   errors,
        'values':   values,
        'is_edit':  True,
        'job_id':   job_id,
    })


def deactivate_job(request, job_id):
    if request.method == 'POST':
        emp_id = request.session.get('employer_id')
        if not emp_id:
            return redirect('authentication:login')

        job = get_object_or_404(JobPost, job_id=job_id, employer=emp_id)
        job.is_active = False
        job.save()
    return redirect(reverse('employer_profile:manage_jobs'))






def profile_manage(request):
    emp_id = request.session.get('employer_id')
    if not emp_id:
        return redirect('authentication:login')
    employer = get_object_or_404(Employer, pk=emp_id)

    # 2) Get or create the one-to-one CompanyProfile
    profile, _ = CompanyProfile.objects.get_or_create(employer=employer)

    # 3) Prepare error & success containers
    errors  = {sec: {} for sec in ('top','password','logo','verify','details')}
    success = {sec: False for sec in errors}


    # 4) Handle form submissions
    if request.method == 'POST':

        if 'submit_top' in request.POST:
            name  = request.POST.get('company_name', '').strip()
            email = request.POST.get('email', '').strip()

            if not name:
                errors['top']['company_name'] = 'Required.'
            elif len(name) > 150:
                errors['top']['company_name'] = 'Max 150 characters.'

            try:
                validate_email(email)
            except ValidationError:
                errors['top']['email'] = 'Invalid email.'

            if not errors['top']:
                employer.company_name = name
                employer.email        = email
                employer.save()
                return redirect(reverse('employer:profile_manage') + '?sec=top&ok=1')

        # — Logo Upload only —
        
        elif 'submit_logo' in request.POST:
            logo = request.FILES.get('logo')

            if not logo:
                errors['logo']['logo'] = 'Required.'
            elif not logo.content_type.startswith('image/'):
                errors['logo']['logo'] = 'Upload a valid image.'
            elif logo.size > 2 * 1024 * 1024:
                errors['logo']['logo'] = 'Max file size is 2 MB.'

            if not errors['logo']:
                profile.logo = logo
                profile.save()
                return redirect(reverse('employer:profile_manage') + '?sec=logo&ok=1')

        # — Verify Certificate —
        elif 'submit_verify' in request.POST:
            cert = request.FILES.get('certificate')
            if not cert:
                errors['verify']['certificate'] = 'Required.'
            elif cert.size > 2*1024*1024:
                errors['verify']['certificate'] = 'Max 2 MB.'
            if not errors['verify']:
                profile.certificate = cert
                profile.certificate_submitted_at = timezone.now()
                profile.save()
                # Optionally, leave employer.is_verified=False until admin action
                return redirect(reverse('employer:profile_manage') + '?sec=verify&ok=1')
            
        elif 'submit_password' in request.POST:
            old_pass  = request.POST.get('old_password', '').strip()
            new_pass  = request.POST.get('new_password', '').strip()
            conf_pass = request.POST.get('confirm_password', '').strip()

            # 1) Verify old password
            if not check_password(old_pass, employer.password):
                errors['password']['old_password'] = 'Incorrect current password.'

            # 2) Validate new password complexity: 6–16 chars, ≥1 digit, ≥1 special
            pw_re = re.compile(r'^(?=.*\d)(?=.*[^\w\s]).{6,16}$')
            if not pw_re.match(new_pass):
                errors['password']['new_password'] = (
                    'Must be 6–16 chars, include at least one number and one special character.'
                )

            # 3) Confirm match
            if new_pass != conf_pass:
                errors['password']['confirm_password'] = 'Does not match the new password.'

            # 4) If valid, save and log out
            if not errors['password']:
                employer.password = make_password(new_pass)
                employer.save()
                request.session.pop('employer_id', None)
                return redirect(reverse('authentication:login'))
    
        # — Details (size, date, phone, address, socials) —
        elif 'submit_details' in request.POST:
            vals = {f: request.POST.get(f,'').strip() for f in (
                'company_size','founded_date','phone_number',
                'address','website','facebook','linkedin','description',
            )}

            # company_size
            if not vals['company_size']:
                errors['details']['company_size'] = 'Required.'

            # founded_date
            fd = vals['founded_date']
            if not fd:
                errors['details']['founded_date'] = 'Required.'
            else:
                try:
                    dobj = datetime.strptime(fd, '%Y-%m-%d').date()
                    if dobj > date.today():
                        errors['details']['founded_date'] = 'Cannot be in future.'
                except ValueError:
                    errors['details']['founded_date'] = 'Invalid date.'

            # phone_number
            if not re.fullmatch(r'\d{10,15}', vals['phone_number']):
                errors['details']['phone_number'] = '10–15 digits required.'

            # address
            if not vals['address']:
                errors['details']['address'] = 'Required.'

            # optional URLs
            for fld in ('website','facebook','linkedin'):
                v = vals[fld]
                if v and not re.match(r'^https?://', v):
                    errors['details'][fld] = 'Must start with http:// or https://'

            desc = vals['description']
            if not desc:
                errors['details']['description'] = 'Required.'
            elif len(desc) < 20:
                errors['details']['description'] = 'At least 20 characters.'

            # Save if ok
            if not errors['details']:
                profile.company_size = vals['company_size']
                profile.founded_date = dobj
                profile.phone_number = vals['phone_number']
                profile.address      = vals['address']
                profile.website      = vals['website']
                profile.facebook     = vals['facebook']
                profile.linkedin     = vals['linkedin']
                profile.description   = desc
                profile.save()
                return redirect(reverse('employer:profile_manage') + '?sec=details&ok=1')

    # 5) After redirect, mark success
    sec = request.GET.get('sec')
    if request.GET.get('ok') == '1' and sec in success:
        success[sec] = True

    # 6) Prepare values for template
    vals = {
        'company_name':    employer.company_name,
        'email':           employer.email,
        'email_notify':    employer.email_notify,
        'representative':  employer.representative_name,
        'joined_time':     employer.joined_time,
        'is_verified':     getattr(employer, 'is_verified', False),
        'company_size':    profile.company_size,
        'founded_date':    profile.founded_date.isoformat() if profile.founded_date else '',
        'phone_number':    profile.phone_number,
        'address':         profile.address,
        'website':         profile.website,
        'facebook':        profile.facebook,
        'linkedin':        profile.linkedin,
        'description':     profile.description, 
    }

    # 7) Render template
    return render(request, 'employer_profile/profile_manage.html', {
        'employer':     employer,
        'profile':      profile,
        'errors':       errors,
        'success':      success,
        'vals':         vals,
        'size_choices': ['1-10','11-50','51-200','201-500','500+'],
    })




@require_POST
def toggle_notify(request):
    emp_id = request.session.get('employer_id')
    if not emp_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=403)

    employer = get_object_or_404(Employer, pk=emp_id)
    try:
        payload = json.loads(request.body)
        new_state = bool(payload.get('email_notify'))
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid payload'}, status=400)

    employer.email_notify = new_state
    employer.save()
    return JsonResponse({'success': True, 'email_notify': new_state})





def update_employer_location(request):
    # require logged-in employer
    eid = request.session.get('employer_id')
    if request.method == 'POST' and eid:
        employer = get_object_or_404(Employer, employer_id=eid)
        try:
            data = json.loads(request.body)
            lat  = float(data.get('lat'))
            lng  = float(data.get('lng'))
        except (ValueError, TypeError, json.JSONDecodeError):
            return JsonResponse({'status':'invalid'}, status=400)

        employer.location = {'lat': lat, 'lng': lng}
        employer.save()
        return JsonResponse({'status':'ok'})
    return JsonResponse({'status':'fail'}, status=403)


 


  

def job_applications(request, job_id):
    eid = request.session.get('employer_id')
    if not eid:
        return redirect('authentication:login')

    employer = get_object_or_404(Employer, employer_id=eid)
    job = get_object_or_404(JobPost, employer=employer, job_id=job_id)

    # base queryset
    base_qs = job.applications.select_related('candidate')

    sort = request.GET.get('sort','')
    if sort == 'old':
        apps_list = list(base_qs.order_by('applied_at'))
    if sort == 'ranked':
        
        premium_obj, _ = EmployerPremium.objects.get_or_create(employer=employer)
        now = timezone.now()
        if not (
            premium_obj.is_subscribed
            and premium_obj.payment_ok
            and premium_obj.subscription_end
            and premium_obj.subscription_end >= now
        ):
            return redirect(reverse('employer:premium'))
        
        apps_list = rank_applications(job, list(base_qs))
    elif sort == 'processing':
        apps_list = base_qs.exclude(status__in=['applied', 'rejected'])   
    elif sort == 'rejected':
        apps_list = base_qs.filter(status='rejected')     
    else:
        apps_list = list(base_qs.order_by('-applied_at'))

    page_obj = Paginator(apps_list, 15).get_page(request.GET.get('page'))

    return render(request, 'employer_profile/job_applications.html', {
        'job': job,
        'page_obj': page_obj,
        'sort': sort,
    })





def application_detail(request, app_id):
    # 1) Auth & ownership check
    eid = request.session.get('employer_id')
    if not eid:
        return redirect('authentication:login')
    employer = get_object_or_404(Employer, employer_id=eid)

    app = get_object_or_404(
        JobApplication.objects.select_related('candidate','job__employer'),
        pk=app_id, job__employer=employer
    )
    job = app.job
    error_date=""
    # 2) Handle state-change POSTs
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'review':
            app.status = 'reviewing'
            app.save()
            # Send notification email to the candidate
            send_mail(
                subject=f"Your application for “{app.job.title}” is under review",
                message=(
                    f"Hi {app.candidate.first_name},\n\n"
                    f"Thank you for applying to “{app.job.title}”.\n"
                    f"Your application is now under review by {app.job.employer.company_name}.\n"
                    "We will be in touch with next steps shortly.\n\n"
                    "Best regards,\n"
                    "The WorkWise Team"
                ),
                from_email="no-reply@workwise.com",
                recipient_list=[app.candidate.email],
                fail_silently=False,
            )
        elif action == 'reject':
            app.status = 'rejected'
            app.save()
            send_mail(
                subject=f"Your application for “{app.job.title}” is Rejected",
                message=(
                    f"Hi {app.candidate.first_name},\n\n"
                    f"Thank you for applying to “{app.job.title}”.\n"
                    f"Your application is rejected by {app.job.employer.company_name}.\n"
                    
                    "The WorkWise Team"
                ),
                from_email="no-reply@workwise.com",
                recipient_list=[app.candidate.email],
                fail_silently=False,
            )
        elif action == 'schedule':
            dt = request.POST.get('interview_at')
            try:
                # from <input type="datetime-local">
                dt_obj = datetime.fromisoformat(dt)
                now = timezone.now()
                if dt_obj < now:
                    error_date = "Interview date/time cannot be in the past."
                else:
                    app.interview_at = dt_obj
                    app.status = 'interview'
                    app.save()
                    send_mail(
                    subject=f"Your application for “{app.job.title}” is under review",
                    message=(
                        f"Hi {app.candidate.first_name},\n\n"
                        f"Thank you for applying to “{app.job.title}”.\n"
                        f"Your application is scheduled for interview by {app.job.employer.company_name}.\n"
                        f"interview time is {app.interview_at}.\n\n"
                        f"please check your email for meeting link forwared by {app.job.employer.company_name}.\n\n"
                        "We will be in touch with next steps shortly.\n\n"
                        "Best regards,\n"
                        "The WorkWise Team"
                    ),
                    from_email="no-reply@workwise.com",
                    recipient_list=[app.candidate.email],
                    fail_silently=False,
                    )
            except Exception:
                messages.error(request, "Invalid date/time format.")

        elif action == 'offer':
            app.status = 'offered'
            app.save()
            messages.success(request, "Offer Extended.")
        return redirect(reverse('employer:application_detail', args=[app_id]))

    return render(request, 'employer_profile/application_detail.html', {
        'app': app,
        'job': job,
        'error_date': error_date,
    })





def interview_applications(request):
    eid = request.session.get('employer_id')
    employer = get_object_or_404(Employer, employer_id=eid)

    apps = JobApplication.objects.select_related('job', 'candidate').filter(
        status='interview', job__employer=employer
    )

    paginator = Paginator(apps, 12)
    page = request.GET.get('page')
    paged_apps = paginator.get_page(page)

    return render(request, 'employer_profile/interview_applications.html', {
        'applications': paged_apps,
        'default_avatar_url': '/static/images/default-user.png',
    })



def send_meeting(request, app_id):
    # 1) Auth & ownership check
    eid = request.session.get('employer_id')
    if not eid:
        return redirect('authentication:login')

    employer = get_object_or_404(Employer, employer_id=eid)
    application = get_object_or_404(
        JobApplication.objects.select_related('candidate', 'job__employer'),
        pk=app_id,
        job__employer=employer
    )

    # 2) Extract & validate form inputs
    message_text   = request.POST.get('message', '').strip()
    meeting_link   = request.POST.get('meeting_link', '').strip()

    if not message_text or not meeting_link:
        messages.error(request, 'Both a message and a meeting link are required.')
        return redirect('employer_profile:interview_applications')
    
    application.meeting_message = message_text
    application.meeting_link    = meeting_link
    application.save()

    # 3) Send email
    subject = f"Interview Invitation for {application.job.title}"
    body    = (
        f"hello, {application.candidate.first_name}\n\n"
        f"{message_text}\n\n"
        f"🔗 Join Meeting: {meeting_link}\n\n"
        "Thanks,\n"
        f"{employer.company_name}"
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [application.candidate.email],
            fail_silently=False,
        )
        messages.success(request, 'Meeting invitation sent to candidate.')
    except Exception as e:
        messages.error(request, f'Error sending email: {e}')

    # 4) Redirect back to the paginated interview list
    return redirect('employer_profile:interview_applications')





def premium(request):
    eid = request.session.get('employer_id')
    if not eid:
        return redirect('authentication:login')
    employer = get_object_or_404(Employer, employer_id=eid)

    premium_obj, _ = EmployerPremium.objects.get_or_create(employer=employer)
    now = timezone.now()
    active = (
        premium_obj.is_subscribed
        and premium_obj.payment_ok
        and premium_obj.subscription_end
        and premium_obj.subscription_end >= now
    )

    return render(request, 'employer_profile/premium.html', {
        'premium': premium_obj,
        'active':  active,
    })



def subscribe_premium(request):
    if request.method == 'POST':
        
        eid = request.session.get('employer_id')
        if not eid:
            return redirect('authentication:login')
        employer = get_object_or_404(Employer, employer_id=eid)

       
        now   = timezone.now()
        term  = relativedelta(months=1)
        price = 2000  


        premium_obj, _ = EmployerPremium.objects.get_or_create(employer=employer)
        premium_obj.is_subscribed    = True
        premium_obj.payment_ok       = True
        premium_obj.subscribed_at    = now
        premium_obj.subscription_end = now + term
        premium_obj.save()

    return redirect(reverse('employer_profile:premium'))





def logout(request):
    request.session.pop('employer_id', None)
    return redirect(reverse('authentication:login'))