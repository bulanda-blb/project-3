
from django.shortcuts import render, get_object_or_404, redirect
from employer_profile.models import JobPost
from django.core.paginator import Paginator
from rapidfuzz import fuzz
from django.utils.safestring import mark_safe
import json
from django.utils import timezone
from candidate_profile.models import SavedJob
from django.db.models   import Q
from django.db.models import Count
from datetime import date
from django.urls import reverse
from django.core.mail import send_mail
from authentication.models import Candidate
from candidate_profile.models import JobApplication
from candidate_profile.models import CandidateCV

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





def home(request):
    base_qs = JobPost.objects.filter(is_active=True, admin_review=False)

    # Top 8 industries by job count
    industry_counts = (
        base_qs
        .values('industry')
        .annotate(count=Count('industry'))
        .order_by('-count')[:8]
    )
    industries_list = [
        {
            'slug':   item['industry'],
            'title':  item['industry'].replace('_',' ').title(),
            'count':  item['count']
        }
        for item in industry_counts
    ]

    # Top 8 departments by job count
    dept_counts = (
        base_qs
        .values('department')
        .annotate(count=Count('department'))
        .order_by('-count')[:8]
    )
    departments_list = [
        {
            'slug':   item['department'],
            'title':  item['department'].replace('_',' ').title(),
            'count':  item['count']
        }
        for item in dept_counts
    ]

    return render(request, 'index/index.html', {
        'industries_list': industries_list,
        'departments_list': departments_list,
    })



def format_label(slug):
    return slug.replace('_', ' ').title()


def job_list(request):
    qs = JobPost.objects.filter(is_active=True, admin_review=False, application_deadline__gte=timezone.now()).select_related('employer__company_profile')
    PAGE_SIZE = 25

    # load saved IDs
    candidate_id = request.session.get('candidate_id')
    if candidate_id:
        saved_job_ids = list(
            SavedJob.objects
                    .filter(candidate_id=candidate_id)
                    .values_list('job__job_id', flat=True)
        )
    else:
        saved_job_ids = []

    print(saved_job_ids)
    # Default (GET): show latest posts
    if request.method != 'POST':
        newest = qs.order_by('-posted_at')
        page   = Paginator(newest, PAGE_SIZE).get_page(request.GET.get('page'))
        return render(request, 'index/jobs_list.html', {
            'jobs': page,
            'industries': [(i, i.replace('_',' ').title()) for i in INDUSTRIES],
            'work_types': [(w, w.replace('_',' ').title()) for w in WORK_TYPES],
            'departments_json': mark_safe(json.dumps(DEPARTMENTS)),
            'filtered': False,
            'saved_job_ids': saved_job_ids,
        })

    # Extract and trim filters
    title    = request.POST.get('title','').strip()
    industry = request.POST.get('industry','').strip()
    dept     = request.POST.get('department','').strip()
    wtype    = request.POST.get('work_type','').strip()
    location = request.POST.get('location','').strip()

    # Must fill all
    if not all([title, industry, dept, wtype, location]):
        return render(request, 'index/jobs_list.html', {
            'jobs': Paginator([], PAGE_SIZE).get_page(1),
            'industries': [(i, i.replace('_',' ').title()) for i in INDUSTRIES],
            'work_types': [(w, w.replace('_',' ').title()) for w in WORK_TYPES],
            'departments_json': mark_safe(json.dumps(DEPARTMENTS)),
            'filtered': True,
            'error_message': 'Please fill in all filter fields.'
        })

    # Prepare buckets
    bucket1, bucket2, bucket3, bucket4 = [], [], [], []

    now = timezone.now()
    for job in qs:
        # Exact matches
        m_ind  = job.industry   == industry
        m_dept = job.department == dept
        m_wt   = job.work_type  == wtype
        exact_count = sum([m_ind, m_dept, m_wt])

        # Fuzzy matches
        loc_score   = fuzz.token_sort_ratio(location.lower(),
                                            job.full_location_address.lower())
        title_score = fuzz.token_sort_ratio(title.lower(),
                                            job.title.lower())

        fuzz_count = ((loc_score   >= 80) + 
                      (title_score >= 60))

        # Recency score (0–1; 1 = just posted, 0 = ≥30 days old)
        days_old     = (now - job.posted_at).days
        recency_score = max(0, (30 - days_old) / 30)

        # Bucket logic:
        if exact_count == 3 and loc_score >= 80 and title_score >= 60:
            bucket1.append((recency_score, job))
        elif exact_count == 3 and title_score >= 60:
            bucket2.append((recency_score, job))
        elif exact_count == 3:
            bucket3.append((recency_score, job))
        elif exact_count + fuzz_count >= 2:
            bucket4.append((recency_score, job))
        # else: discard jobs with <2 total matches

    # Within each bucket, sort by recency (desc)
    def sort_bucket(b): 
        return [job for _, job in sorted(b, key=lambda x: x[0], reverse=True)]

    final_jobs = (
        sort_bucket(bucket1) +
        sort_bucket(bucket2) +
        sort_bucket(bucket3) +
        sort_bucket(bucket4)
    )

    # Paginate
    page = Paginator(final_jobs, PAGE_SIZE).get_page(request.GET.get('page'))

    return render(request, 'index/jobs_list.html', {
        'jobs': page,
        'industries': [(i, i.replace('_',' ').title()) for i in INDUSTRIES],
        'work_types': [(w, w.replace('_',' ').title()) for w in WORK_TYPES],
        'departments_json': mark_safe(json.dumps(DEPARTMENTS)),
        'filtered': True,
        'searched_title': title,
        'searched_location': location,
        'saved_job_ids': saved_job_ids,
    })






def explore_jobs(request, filter_type, keyword):
    base_qs = (
        JobPost.objects
        .filter(is_active=True, admin_review=False)
        .select_related('employer__company_profile')
    )

    # 1) Initial filter by URL type
    if filter_type == 'industry':
        qs = base_qs.filter(industry__iexact=keyword)
    elif filter_type == 'department':
        qs = base_qs.filter(department__iexact=keyword)
    elif filter_type == 'title':
        # keyword might be slugified: replace hyphens/underscores with spaces
        text = keyword.replace('-', ' ').replace('_',' ')
        qs = base_qs.filter(title__icontains=text)
    else:
        qs = base_qs.none()

    display_label = keyword.replace('_',' ').replace('-',' ').title()

    # 2) Search within these results
    search = request.GET.get('q','').strip()
    if search:
        qs = qs.filter(title__icontains=search)

    # 3) Order & paginate
    qs = qs.order_by('-posted_at')
    page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))

    # 4) Saved‐job IDs for current candidate
    cid = request.session.get('candidate_id')
    if cid:
        saved_ids = list(
            SavedJob.objects
                .filter(candidate_id=cid)
                .values_list('job__job_id', flat=True)
        )
    else:
        saved_ids = []

    return render(request, 'index/explore_jobs.html', {
        'jobs': page_obj,
        'filter_type': filter_type,
        'display_label': display_label,
        'search_keyword': search,
        'saved_job_ids': saved_ids,
        'keyword': keyword,
    })







def job_details(request, job_id):
    # require candidate
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect(f"{reverse('authentication:login')}?next={request.path}")
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    try:
        cv_obj = candidate.cv
        has_cv = bool(cv_obj.cv_file)
    except CandidateCV.DoesNotExist:
        has_cv = False

    job = get_object_or_404(
        JobPost.objects.select_related('employer__company_profile'),
        job_id=job_id, is_active=True, admin_review=False
    )

    has_applied = JobApplication.objects.filter(candidate=candidate, job=job).exists()
    error = None

    if request.method == 'POST' and not has_applied:
        if not has_cv:
            return redirect(reverse('candidate:upload_cv'))
        
        f = request.FILES.get('cover_letter')
        if not f:
            error = 'Please upload a cover letter.'
        elif f.size > 2*1024*1024:
            error = 'File too large (max 2MB).'
        else:
            app = JobApplication.objects.create(
                candidate=candidate,
                job=job,
                cover_letter=f
            )
            send_mail(
                f"Application Received: {job.title}",
                f"Hi {candidate.first_name},\n\n"
                f"You’ve applied for “{job.title}”.\n"
                f"Thank you!\n",
                'no-reply@workwise.com',
                [candidate.email],
            )
            return redirect('candidate:applied_jobs')

    days_remaining = max((job.application_deadline - date.today()).days, 0)
    return render(request, 'index/job-details.html', {
        'job': job,
        'days_remaining': days_remaining,
        'has_applied': has_applied,
        'error': error,
    })
