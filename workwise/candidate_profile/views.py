from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import json, os, re
from django.http import JsonResponse, HttpResponseBadRequest
from authentication.models import Candidate
from employer_profile.models import JobPost
from .models import SavedJob
from django.http import JsonResponse, HttpResponseForbidden
from django.core.mail import send_mail
from .models import JobApplication
from django.core.paginator import Paginator
from datetime import timedelta
from django.utils.timezone import now
from .models               import CandidateCV, CandidatePremium
from utils.text_extractor  import extract_text_from_file
from utils.resume_parser   import parse_resume
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.conf import settings
import math
import openai
import traceback
from openai import OpenAI
openai.api_key = settings.OPENAI_API_KEY

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise  import cosine_similarity
from rapidfuzz import fuzz


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


def dashboard(request):
    # — Authentication —
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect('authentication:login')
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    # — Summary counts —
    total_apps      = candidate.applications.count()
    pending_reviews = candidate.applications.filter(status='reviewing').count()
    interviews      = candidate.applications.filter(status='interview').count()
    offers          = candidate.applications.filter(status='offered').count()
    saved_jobs      = candidate.saved_jobs.count()

    # — Status distribution for pie chart —
    statuses     = ['applied','reviewing','interview','offered','rejected']
    status_labels = ['Applied','Reviewing','Interview','Offered','Rejected']
    status_data   = [candidate.applications.filter(status=s).count() for s in statuses]

    # — Activity over last 6 months for line chart —
    now = timezone.now()
    activity_labels = []
    activity_data   = []
    for i in reversed(range(6)):
        m = now - relativedelta(months=i)
        label = m.strftime('%b %Y')
        cnt = candidate.applications.filter(
            applied_at__year=m.year,
            applied_at__month=m.month
        ).count()
        activity_labels.append(label)
        activity_data.append(cnt)

    # — Upcoming interviews (next 5) —
    upcoming = candidate.applications.filter(
        status='interview',
        interview_at__gte=now
    ).order_by('interview_at')[:5]

    # — Profile completeness (4 checks) —
    has_picture    = bool(candidate.profile_picture)
    has_cv         = hasattr(candidate, 'cv')
    parsed         = getattr(candidate, 'cv', None)
    has_parsed     = bool(parsed and parsed.parsed_data)
    has_location   = bool(candidate.location)

    criteria = [
        ('Profile Picture', has_picture),
        ('Uploaded CV',     has_cv),
        ('Parsed CV Data',  has_parsed),
        ('Location Info',   has_location),
    ]
    weight = 100 / len(criteria)
    segments = []
    for name, done in criteria:
        segments.append({
            'name': name,
            'done': done,
            'width': weight,
        })

    done_count = sum(1 for seg in segments if seg['done'])
    completeness = int(done_count / len(segments) * 100)
    return render(request, 'candidate_profile/dashboard.html', {
        'total_apps': total_apps,
        'pending_reviews': pending_reviews,
        'interviews': interviews,
        'offers': offers,
        'saved_jobs': saved_jobs,
        'status_labels_json': json.dumps(status_labels),
        'status_data_json':   json.dumps(status_data),
        'activity_labels_json': json.dumps(activity_labels),
        'activity_data_json':   json.dumps(activity_data),
        'upcoming_interviews': upcoming,
        'profile_segments': segments,
        'profile_completeness': completeness,
        'candidate': candidate,
    })





def profile_manage(request):
    # Ensure candidate is logged in
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect(f"{reverse('authentication:login')}?next={reverse('candidate:profile_manage')}")

    candidate = get_object_or_404(Candidate, candidate_id=cid)
    errors    = {}
    success   = {}

    if request.method == 'POST':
        section = request.POST.get('section')

        # 1) Name & Email
        if section == 'top':
            fn = request.POST.get('first_name','').strip()
            ln = request.POST.get('last_name','').strip()
            em = request.POST.get('email','').strip()
            if not fn or not ln or not em:
                errors['top'] = 'All fields are required.'
            else:
                candidate.first_name = fn
                candidate.last_name  = ln
                candidate.email      = em
                candidate.save()
                success['top'] = 'Your name & email have been updated.'

        # 2) Profile picture
        elif section == 'pic':
            pic = request.FILES.get('picture')
            if not pic:
                errors['pic'] = 'Please select an image file.'
            else:
                if pic.size > 2*1024*1024:
                    errors['pic'] = 'Image must be under 2MB.'
                else:
                    candidate.profile_picture = pic
                    candidate.save()
                    success['pic'] = 'Profile picture updated.'

        # 3) Password change
        elif section == 'password':
            old = request.POST.get('old_password','')
            new = request.POST.get('new_password','')
            cf  = request.POST.get('confirm_password','')
            pwd_err = {}

            # 1) Verify the old password
            if not check_password(old, candidate.password):
                pwd_err['old_password'] = 'Incorrect current password.'

            # 2) Validate new password
            if not new:
                pwd_err['new_password'] = 'New password required.'
            elif len(new) < 6 or len(new) > 16:
                pwd_err['new_password'] = 'Must be 6–16 characters.'
            if new != cf:
                pwd_err['confirm_password'] = 'Passwords do not match.'

            # 3) If errors, send back; otherwise hash & save
            if pwd_err:
                errors['password'] = pwd_err
            else:
                candidate.password = make_password(new)
                candidate.save()
                success['password'] = 'Password changed. Please log in again.'
                request.session.pop('candidate_id', None)
                return redirect(reverse('authentication:login'))

    return render(request, 'candidate_profile/profile.html', {
        'candidate': candidate,
        'errors':    errors,
        'success':   success,
    })


def toggle_notify(request):
    if request.method=='POST' and request.session.get('candidate_id'):
        cand = get_object_or_404(Candidate, candidate_id=request.session['candidate_id'])
        cand.email_notify = not cand.email_notify
        cand.save()
        return JsonResponse({'status':'ok','notify':cand.email_notify})
    return JsonResponse({'status':'fail'}, status=400)




def update_location(request):
    if request.method == 'POST' and request.session.get('candidate_id'):
        candidate = get_object_or_404(
            Candidate, candidate_id=request.session['candidate_id']
        )
        try:
            payload = json.loads(request.body)
            lat = float(payload.get('lat'))
            lng = float(payload.get('lng'))
        except (ValueError, TypeError, json.JSONDecodeError):
            return JsonResponse({'status':'invalid'}, status=400)

        candidate.location = {'lat': lat, 'lng': lng}
        candidate.save()
        return JsonResponse({'status':'ok'})
    return JsonResponse({'status':'fail'}, status=403)




def save_job(request):
    if request.method != 'POST':
        return HttpResponseBadRequest()
    try:
        data = json.loads(request.body)
        job_id = int(data.get('job_id'))
    except:
        return JsonResponse({'error':'invalid payload'}, status=400)

    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return JsonResponse({'redirect': reverse('authentication:signup_candidate')}, status=403)

    try:
        candidate = Candidate.objects.get(pk=candidate_id)
        job = JobPost.objects.get(job_id=job_id)
    except (Candidate.DoesNotExist, JobPost.DoesNotExist):
        return JsonResponse({'error':'not found'}, status=404)

    obj, created = SavedJob.objects.get_or_create(candidate=candidate, job=job)
    if not created:
        obj.delete()
        return JsonResponse({'status':'unsaved'})
    return JsonResponse({'status':'saved'})




def saved_jobs(request):
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('authentication:login')

    candidate = get_object_or_404(Candidate, candidate_id=candidate_id)

    # Read sort param
    sort_order = request.GET.get('sort', 'newest')

    # Base queryset
    qs = (
        SavedJob.objects
        .filter(candidate=candidate)
        .select_related('job__employer__company_profile')
    )

    # Apply sort
    if sort_order == 'oldest':
        qs = qs.order_by('saved_at')
    else:  # newest
        qs = qs.order_by('-saved_at')

    # Paginate
    page = Paginator(qs, 20).get_page(request.GET.get('page'))

    return render(request, 'candidate_profile/saved_jobs.html', {
        'page_obj':    page,
        'current_sort': sort_order,
    })



def applied_jobs(request):
    # — Authentication —
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect(f"{reverse('authentication:login')}?next={request.path}")
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    # — Read filters/sort from querystring —
    status_filter = request.GET.get('status', 'all')
    sort_order    = request.GET.get('sort',   'newest')

    # Build status dropdown options: “All” + model’s choices
    status_choices = [('all', 'All')] + list(JobApplication.STATUS_CHOICES)

    # — Base queryset —
    qs = JobApplication.objects.filter(candidate=candidate) \
           .select_related('job__employer__company_profile')

    # — Apply status filter —
    if status_filter != 'all':
        qs = qs.filter(status=status_filter)

    # — Apply sort —
    if sort_order == 'oldest':
        qs = qs.order_by('applied_at')
    else:  
        qs = qs.order_by('-applied_at')

    # — Paginate (8 per page) —
    page = Paginator(qs, 8).get_page(request.GET.get('page'))

    return render(request, 'candidate_profile/applied_jobs.html', {
        'applications':   page,
        'status_choices': status_choices,
        'current_status': status_filter,
        'current_sort':   sort_order,
    })




def application_detail(request, application_id):
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect(f"{reverse('authentication:login')}?next={request.path}")

    application = get_object_or_404(
        JobApplication.objects
          .select_related('job__employer__company_profile'),
        pk=application_id,
        candidate_id=cid
    )

    # Progress steps
    steps = [
      {'key':'applied',   'label':'Applied'},
      {'key':'reviewing', 'label':'Under Review'},
      {'key':'interview', 'label':'Interview Scheduled'},
      {'key':'offered',   'label':'Offer Extended'},
      {'key':'rejected',  'label':'Rejected'},
    ]
    current = [s['key'] for s in steps].index(application.status)

    return render(request, 'candidate_profile/application_detail.html', {
      'application': application,
      'steps': steps,
      'current_step': current,
    })






def upload_and_review_cv(request):
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect(f"{reverse('authentication:login')}?next={request.path}")
    
    candidate = get_object_or_404(Candidate, candidate_id=cid)
    cv_obj, _ = CandidateCV.objects.get_or_create(candidate=candidate)

    parsed = None
    error  = None

    if request.method == 'POST':
        # FINAL SAVE
        if request.POST.get('action') == 'save':
            existing = cv_obj.parsed_data or {}
            data = {}
            # simple fields
            for key in ('name','email','phone','address','summary'):
                data[key] = request.POST.get(key) or existing.get(key)

            # list fields: comma for skills, certs, languages, hobbies; newline for edu/exp/achievements
            def pull_list(field, delim=','):
                raw = request.POST.get(field)
                if raw:
                    return [v.strip() for v in raw.split(delim) if v.strip()]
                return existing.get(field, [])

            data['skills']         = pull_list('skills', delim=',')
            data['certifications'] = pull_list('certifications', delim=',')
            data['languages']      = pull_list('languages', delim=',')
            data['hobbies']        = pull_list('hobbies', delim=',')
            data['education']      = pull_list('education','\n')
            data['experience']     = pull_list('experience','\n')
            data['achievements']   = pull_list('achievements','\n')

            # projects: assume JSON textarea named 'projects_json'
            try:
                proj_raw = request.POST.get('projects_json','[]')
                data['projects'] = json.loads(proj_raw)
            except Exception:
                data['projects'] = existing.get('projects', [])

            cv_obj.parsed_data = data
            cv_obj.save()
            return redirect('candidate:upload_cv')

        # UPLOAD & PARSE
        f = request.FILES.get('cv_file')
        if not f:
            error = 'Please select a file.'
        else:
            ext = f.name.lower().rsplit('.',1)[-1]
            if ext not in ('pdf','docx','png','jpg','jpeg'):
                error = 'Invalid file type.'
            elif f.size > 2*1024*1024:
                error = 'File must be under 2MB.'
            else:
                cv_obj.cv_file.save(f.name, f)
                cv_obj.save()
                text = extract_text_from_file(cv_obj.cv_file.path)
                try:
                    parsed = parse_resume(text)

                except Exception as e:
                    traceback.print_exc()
                    error = f"Parsing failed: {str(e)}"

    return render(request, 'candidate_profile/upload_cv.html', {
        'cv_obj': cv_obj,
        'parsed': parsed,
        'error':  error,
    })



def clear_cv(request):
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect(f"{reverse('authentication:login')}?next={reverse('candidate:upload_cv')}")
    candidate = get_object_or_404(Candidate, candidate_id=cid)
    try:
        cv = CandidateCV.objects.get(candidate=candidate)
        cv.delete()
    except CandidateCV.DoesNotExist:
        pass
    return redirect('candidate:upload_cv')




def interview_list(request):
    # 1) Auth
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect('authentication:login')
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    # 2) Base QS: only status='interview'
    base_qs = JobApplication.objects.select_related(
        'job__employer__company_profile'
    ).filter(
        candidate=candidate,
        status='interview'
    )

    # 3) when filter
    when = request.GET.get('when', 'all')
    now   = timezone.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    nextday  = today + timedelta(days=2)

    if when == 'today':
        filtered = base_qs.filter(interview_at__date=today).order_by('interview_at')
    elif when == 'tomorrow':
        filtered = base_qs.filter(interview_at__date=tomorrow).order_by('interview_at')
    elif when == 'nextday':
        filtered = base_qs.filter(interview_at__date=nextday).order_by('interview_at')
    elif when == 'past':
        filtered = base_qs.filter(interview_at__lt=now).order_by('-interview_at')
    else:  # 'all'
        upcoming = list(base_qs.filter(interview_at__gte=now).order_by('interview_at'))
        past     = list(base_qs.filter(interview_at__lt=now).order_by('-interview_at'))
        filtered = upcoming + past

    # 4) Paginate (8 per page)
    page_num = request.GET.get('page')
    page = Paginator(filtered, 8).get_page(page_num)

    return render(request, 'candidate_profile/interview_list.html', {
        'applications': page,
        'current_when': when,
    })



client = OpenAI()
def skill_gap(request):
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect('authentication:login')
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    premium_obj, _ = CandidatePremium.objects.get_or_create(candidate=candidate)
    now = timezone.now()
    if not (premium_obj.is_subscribed and
            premium_obj.payment_ok and
            premium_obj.subscription_end and
            premium_obj.subscription_end >= now):
        return redirect('candidate:premium')
    
    # Prefill from CV
    cv = getattr(candidate, 'cv', None)
    parsed = cv.parsed_data if cv and cv.parsed_data else {}
    initial_skills     = parsed.get('skills', [])
    initial_title      = parsed.get('current_job_title', '')
    initial_industry   = parsed.get('industry', '')
    initial_department = parsed.get('department', '')
    initial_experience = parsed.get('experience_years', '')

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            body       = json.loads(request.body)
            skills     = body['skills']
            job_title  = body['job_title']
            industry   = body['industry']
            department = body['department']
            experience = body['experience']

            # Build prompt with explicit JSON‐only instruction
            prompt = f"""
You are an expert career coach. Return *only* valid JSON—nothing else.

Candidate Skills: {skills}
Job Title: {job_title}
Industry: {industry}
Department: {department}
Experience: {experience} years

1. List at most 5 required or preferred skills the candidate is missing.
2. For each, provide actionable guidance on how to master it (as a single JSON string).

Output JSON:
[
  {{
    "skill": "skill_name",
    "guidance": "…guidance text…"
  }},
  …
]
"""
            
            try:
                
                resp = client.responses.create(model="gpt-4.1", input=prompt)
            except NameError:
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"system","content":"You are an expert career coach."},
                              {"role":"user","content":prompt}],
                    temperature=0
                )

            raw = ""
            if hasattr(resp, "output"):
                # new SDK path
                for msg in resp.output:
                    # msg.content is a list of chunk‐objects
                    chunks = getattr(msg, "content", None)
                    if isinstance(chunks, list):
                        for chunk in chunks:
                            # chunk.type == "output_text"
                            if getattr(chunk, "type", None) == "output_text":
                                raw += getattr(chunk, "text", "")
                    elif isinstance(chunks, str):
                        raw += chunks

            elif hasattr(resp, "choices"):
                # fallback to ChatCompletion
                raw = resp.choices[0].message.content

            else:
                # ultimate fallback
                raw = str(resp)

            # strip fences & whitespace
            raw = raw.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            # 3) Parse JSON
            suggestions = json.loads(raw)
            return JsonResponse({'suggestions': suggestions})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON from API', 'raw': raw}, status=500)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return render(request, 'candidate_profile/skill_gap.html', {
        'industries': INDUSTRIES,
        'departments_json': json.dumps(DEPARTMENTS),
        'initial_skills': ', '.join(initial_skills),
        'initial_title': initial_title,
        'initial_industry': initial_industry,
        'initial_department': initial_department,
        'initial_experience': initial_experience,
    })




def haversine(lat1, lon1, lat2, lon2):
    # returns distance in km between two lat/lon
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def premium_recommendations(request):
    # — 1) Auth & Premium Check —
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect('authentication:login')
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    premium_obj, _ = CandidatePremium.objects.get_or_create(candidate=candidate)
    now = timezone.now()
    if not (premium_obj.is_subscribed and premium_obj.payment_ok
            and premium_obj.subscription_end and premium_obj.subscription_end >= now):
        return redirect(reverse('candidate_profile:premium'))

    # — 2) Candidate Data Extraction —
    cv     = getattr(candidate, 'cv', None)
    parsed = cv.parsed_data if cv and cv.parsed_data else {}
    cand_skills  = set(parsed.get('skills', []))
    cand_langs   = set(parsed.get('languages', []))
    cand_title   = parsed.get('current_job_title','') or ''
    cand_exp_yrs = parsed.get('experience_years', 0) or 0
    cand_loc     = candidate.location or {}
    clat, clng   = cand_loc.get('lat'), cand_loc.get('lng')

    # — 3) Fetch Active Jobs —
    jobs = list(JobPost.objects.filter(is_active=True)
                .select_related('employer__company_profile'))

    # — 4) Precompute Description Vectors (TF-IDF) —
    docs = [job.description or "" for job in jobs]
    cv_text = " ".join(filter(None, [
      parsed.get('summary',''),
      *parsed.get('experience',[]),
      *parsed.get('education',[]),
      *[p.get('description','') for p in parsed.get('projects',[])]
    ]))
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    tfidf_all  = vectorizer.fit_transform(docs + [cv_text])
    job_vecs   = tfidf_all[:-1]
    cv_vec     = tfidf_all[-1]

    # — 5) Compute Distances & find max for normalization —
    distances = []
    for job in jobs:
        jl = job.map_location or {}
        if clat and clng and jl.get('lat') and jl.get('lng'):
            distances.append(haversine(clat, clng, jl['lat'], jl['lng']))
        else:
            distances.append(None)
    max_dist = max((d for d in distances if d is not None), default=1)

    # — 6) Build Recommendation List with Feature Scores —
    recs = []
    for idx, job in enumerate(jobs):
        # Skip if no skill overlap
        reqs       = set(job.requirements or [])
        prefs      = set(job.preferred_skills or [])
        all_skills = reqs | prefs
        shared     = cand_skills & all_skills
        if not shared:
            continue

        # a) Skill Jaccard
        skill_jacc = len(shared) / len(all_skills)

        # b) Requirement-only Jaccard
        req_jacc   = (len(cand_skills & reqs) / len(reqs)) if reqs else 0

        # c) Industry / Department match
        ind_score = 1 if parsed.get('industry') == job.industry else 0
        dep_score = 1 if parsed.get('department') == job.department else 0

        # d) Title fuzzy similarity
        title_score = fuzz.token_set_ratio(cand_title, job.title) / 100

        # e) Language overlap
        langs = set(job.languages or [])
        lang_score = len(cand_langs & langs) / len(langs) if langs else 0

        # f) Description cosine similarity
        desc_score = cosine_similarity(job_vecs[idx], cv_vec.reshape(1,-1))[0,0]

        # g) Experience fit (safe)
        exp_score = 0.5
        min_exp, max_exp = job.experience_min, job.experience_max
        if min_exp is not None and max_exp is not None:
            if max_exp > min_exp:
                if cand_exp_yrs < min_exp:
                    exp_score = cand_exp_yrs / min_exp
                elif cand_exp_yrs > max_exp:
                    exp_score = 1.0
                else:
                    exp_score = (cand_exp_yrs - min_exp) / (max_exp - min_exp)
            else:
                exp_score = 1.0 if cand_exp_yrs >= min_exp else 0.0

        # h) Intern penalty
        pen = 0.5 if 'intern' in job.title.lower() and cand_exp_yrs >= 2 else 1.0

        # i) Distance normalization
        d = distances[idx]
        dist_score = 1 - min(d/max_dist, 1) if d is not None else 0

        # j) Composite weighted score
        weights = {
            'skill': 0.30,
            'req':   0.20,
            'desc':  0.15,
            'ind':   0.10,
            'dep':   0.05,
            'title': 0.05,
            'lang':  0.05,
            'exp':   0.05,
            'dist':  0.05,
        }
        composite = (
            weights['skill'] * skill_jacc +
            weights['req']   * req_jacc +
            weights['desc']  * desc_score +
            weights['ind']   * ind_score +
            weights['dep']   * dep_score +
            weights['title'] * title_score +
            weights['lang']  * lang_score +
            weights['exp']   * exp_score +
            weights['dist']  * dist_score
        ) * pen

        recs.append({
            'job':            job,
            'score':          composite,
            'matched_skills': sorted(shared),
            'match_count':    len(shared),
            'distance':       d,
            'posted_at':      job.posted_at,
        })

    # — 7) Sort Based on User’s Choice —
    sort = request.GET.get('sort', 'recommended')
    if sort == 'newest':
        recs.sort(key=lambda x: x['posted_at'], reverse=True)
    elif sort == 'oldest':
        recs.sort(key=lambda x: x['posted_at'])
    else: 
        recs.sort(
        key=lambda x: (
            -x['score'],
            x['distance'] if x['distance'] is not None else float('inf')
        )
    )

    # — 8) Paginate & Render —
    page = Paginator(recs, 12).get_page(request.GET.get('page'))
    return render(request, 'candidate_profile/premium_recommendations.html', {
        'recommendations': page,
        'current_sort':    sort,
    })




def premium(request):
    cid = request.session.get('candidate_id')
    if not cid:
        return redirect('authentication:login')
    candidate = get_object_or_404(Candidate, candidate_id=cid)

    premium_obj, _ = CandidatePremium.objects.get_or_create(candidate=candidate)
    # Check active subscription
    now = timezone.now()
    active = premium_obj.payment_ok and premium_obj.subscription_end and premium_obj.subscription_end >= now

    return render(request, 'candidate_profile/premium.html', {
        'premium': premium_obj,
        'active':  active,
    })

def subscribe_premium(request):
    if request.method == 'POST':
        cid = request.session.get('candidate_id')
        if not cid:
            return redirect('authentication:login')
        candidate, _ = get_object_or_404(Candidate, candidate_id=cid), None
        premium_obj, _ = CandidatePremium.objects.get_or_create(candidate=candidate)

        now = timezone.now()
        premium_obj.is_subscribed    = True
        premium_obj.payment_ok       = True
        premium_obj.subscribed_at    = now
        premium_obj.subscription_end = now + relativedelta(months=1)
        premium_obj.save()

    return redirect(reverse('candidate:premium'))


def logout(request):
    request.session.pop('candidate_id', None)
    return redirect(reverse('authentication:login'))