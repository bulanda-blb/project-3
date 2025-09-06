import re
import random
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from django.conf import settings
from .models import Candidate, Employer

def signup(request):
    return render(request, 'authentication/signup.html')


def signup_candidate(request):
    errors = []
    form_data = {
        'first_name': '',
        'last_name': '',
        'email': '',
        'email_notify': False,
        'agree_terms': False,
    }

    if request.method == 'POST':
        form_data['first_name']   = request.POST.get('first_name', '').strip()
        form_data['last_name']    = request.POST.get('last_name', '').strip()
        form_data['email']        = request.POST.get('email', '').strip()
        password                  = request.POST.get('password', '')
        confirm_password          = request.POST.get('confirm_password', '')
        form_data['email_notify'] = bool(request.POST.get('email_notify'))
        form_data['agree_terms']  = bool(request.POST.get('agree_terms'))

        name_re  = re.compile(r'^[A-Za-z]+$')
        email_re = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        pwd_re   = re.compile(r'^(?=.*\d)(?=.*[!@#$%^&*]).{6,16}$')

        if not name_re.match(form_data['first_name']):
            errors.append('first name must contain only letters')
        if not name_re.match(form_data['last_name']):
            errors.append('last name must contain only letters')
        if not email_re.match(form_data['email']):
            errors.append('enter a valid email address')
        if Candidate.objects.filter(email=form_data['email']).exists():
            errors.append('that email is already registered')    
        if not pwd_re.match(password):
            errors.append('password must be 6–16 chars with at least one number & special character')
        if password != confirm_password:
            errors.append('passwords do not match')
        if not form_data['agree_terms']:
            errors.append('you must agree to the terms and conditions')

        if errors:
            return render(request, 'authentication/signup-candidate.html', {
                'errors': errors,
                'form_data': form_data
            })

        otp = f"{random.randint(100000, 999999):06d}"
        print(f'otp is {otp}')
        now_ts = timezone.now().timestamp()

        request.session['candidate_signup_data'] = {
            'first_name':    form_data['first_name'],
            'last_name':     form_data['last_name'],
            'email':         form_data['email'],
            'password':      make_password(password),
            'email_notify':  form_data['email_notify'],
            'agree_terms':   form_data['agree_terms'],
            'otp':           otp,
            'otp_sent_time': now_ts,
        }
        request.session['show_loc_prompt'] = True
        subject = "Your WorkWise Verification Code"
        message = (
            f"Hello {form_data['first_name']},\n\n"
            f"Your verification code is: {otp}\n"
            "It will expire in 15 minutes.\n\n"
            "If you did not request this, please ignore this email.\n\n"
            "Thank you,\nThe WorkWise Team"
        )
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [form_data['email']],
            fail_silently=False,
        )

        return redirect('auth:verify_email_candidate')

    return render(request, 'authentication/signup-candidate.html', {
        'errors': errors,
        'form_data': form_data
    })





def verify_email_candidate(request):
    data = request.session.get('candidate_signup_data')
    if not data:
        return redirect('auth:signup_candidate')

    show_loc_prompt = request.session.pop('show_loc_prompt', False)
    # TTL check: 15 min = 900 seconds
    now_ts = timezone.now().timestamp()
    if now_ts - data['otp_sent_time'] > 900:
        request.session.pop('candidate_signup_data', None)
        return redirect('auth:signup_candidate')

    last_ts = data.get('otp_sent_time', 0)
    elapsed = now_ts - last_ts
    # Compute cooldown remaining (30s)
    resend_cooldown = max(0, 30 - int(elapsed))

    error = None
    modal_error = None
    # Handle email edit
    if request.method == 'POST' and 'edit_email' in request.POST:
        new_email = request.POST.get('new_email','').strip()
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', new_email):
            error = 'enter a valid email address'
        # duplicate check
        elif Candidate.objects.filter(email=new_email).exists():
            error = 'that email is already registered'
        else:
            # update session, resend OTP...
            otp = f"{random.randint(100000,999999):06d}"
            print(f'otp is {otp}')
            now_ts = timezone.now().timestamp()
            data['email'] = new_email
            data['otp'] = otp
            data['otp_sent_time'] = now_ts
            request.session['candidate_signup_data'] = data
            send_mail(
                "Your WorkWise Verification Code",
                f"Hello {data['first_name']},\nYour new code is {otp}\nExpires in 15 minutes.",
                settings.EMAIL_HOST_USER,
                [new_email],
                fail_silently=False,
            )
            return redirect('auth:verify_email_candidate')

    # Handle OTP verify
    elif request.method == 'POST' and 'verify_submit' in request.POST:
        code = request.POST.get('verification_code','').strip()
        lat  = request.POST.get('latitude')
        lng  = request.POST.get('longitude')
        if code != data.get('otp'):
            error = 'invalid verification code'
        else:
            # Save Candidate
            cand = Candidate(
                first_name   = data['first_name'],
                last_name    = data['last_name'],
                email        = data['email'],
                password     = data['password'],
                email_notify = data['email_notify'],
                agree_terms  = data['agree_terms'],
                ip_address   = request.META.get('REMOTE_ADDR'),
                location     = {'lat': float(lat), 'lng': float(lng)} if lat and lng else None
            )
            cand.is_active = True
            cand.save()
            # cleanup
            request.session.pop('candidate_signup_data', None)
            return redirect(f"{reverse('auth:login')}?registered=1")

    return render(request, 'authentication/verify-email-candidate.html', {
        'email': data['email'],
        'error': error,
        'seconds_since_send': int(now_ts - data['otp_sent_time']),
        'show_loc_prompt': show_loc_prompt,
        'resend_cooldown': resend_cooldown,
        'modal_error': modal_error,
    })



def resend_code_candidate(request):
    data = request.session.get('candidate_signup_data')
    if not data:
        return redirect('auth:signup_candidate')

    now_ts = timezone.now().timestamp()
    # Enforce 30s between sends
    if now_ts - data.get('otp_sent_time', 0) < 30:
        return redirect('auth:verify_email_candidate')

    # Generate new OTP and update timestamp
    otp = f"{random.randint(100000,999999):06d}"
    print(f'otp is {otp}')
    data['otp'] = otp
    data['otp_sent_time'] = now_ts
    request.session['candidate_signup_data'] = data

    # Send the email
    send_mail(
        "Your WorkWise Verification Code",
        f"Hello {data['first_name']},\nYour new code is {otp}\nExpires in 15 minutes.",
        settings.EMAIL_HOST_USER,
        [data['email']],
        fail_silently=False,
    )

    return redirect('auth:verify_email_candidate')





  

def signup_employer(request):
    errors = []
    form_data = {
        'company_name': '',
        'representative_name': '',
        'email': '',
        'email_notify': False,
        'agree_terms': False,
    }

    if request.method == 'POST':
        form_data['company_name']        = request.POST.get('company_name','').strip()
        form_data['representative_name'] = request.POST.get('representative_name','').strip()
        form_data['email']               = request.POST.get('email','').strip()
        password                         = request.POST.get('password','')
        confirm_password                 = request.POST.get('confirm_password','')
        form_data['email_notify']        = bool(request.POST.get('email_notify'))
        form_data['agree_terms']         = bool(request.POST.get('agree_terms'))

        # Regex patterns
        company_re = re.compile(r'^[A-Za-z0-9 ]+$')
        name_re  = re.compile(r'^[A-Za-z ]+$')
        email_re = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        pwd_re   = re.compile(r'^(?=.*\d)(?=.*[!@#$%^&*]).{6,16}$')

        # Validation
        if not company_re.match(form_data['company_name']):
            errors.append('company name must contain only letters and spaces')
        if not name_re.match(form_data['representative_name']):
            errors.append('representative name must contain only letters and spaces')
        if not email_re.match(form_data['email']):
            errors.append('enter a valid email address')
        if Employer.objects.filter(email=form_data['email']).exists():
            errors.append('that email is already registered')
        if not pwd_re.match(password):
            errors.append('password must be 6–16 chars with at least one number & special character')
        if password != confirm_password:
            errors.append('passwords do not match')
        if not form_data['agree_terms']:
            errors.append('you must agree to the terms and conditions')

        if errors:
            return render(request, 'authentication/signup-employer.html', {
                'errors': errors,
                'form_data': form_data
            })

        # Generate OTP & stash in session
        otp = f"{random.randint(100000,999999):06d}"
        print(otp)
        now_ts = timezone.now().timestamp()
        request.session['employer_signup_data'] = {
            'company_name':        form_data['company_name'],
            'representative_name': form_data['representative_name'],
            'email':               form_data['email'],
            'password':            make_password(password),
            'email_notify':        form_data['email_notify'],
            'agree_terms':         form_data['agree_terms'],
            'otp':                 otp,
            'otp_sent_time':       now_ts,
        }

        # Send OTP email
        send_mail(
            "Your WorkWise Employer Verification Code",
            f"Hello {form_data['representative_name']},\nYour code is {otp}\nExpires in 15 min.",
            settings.EMAIL_HOST_USER,
            [form_data['email']],
            fail_silently=False,
        )
        request.session['show_loc_prompt'] = True
        return redirect('auth:verify_email_employer')

    return render(request, 'authentication/signup-employer.html', {
        'errors': errors,
        'form_data': form_data
    })


def verify_email_employer(request):
    data = request.session.get('employer_signup_data')
    if not data:
        return redirect('auth:signup_employer')

    # Pop the flag so “Location access granted” only shows once after signup
    show_loc_prompt = request.session.pop('show_loc_prompt', False)

    error = None
    modal_error = None

    # — Handle edit-email submission —
    if request.method == 'POST' and 'edit_email' in request.POST:
        new_email = request.POST.get('new_email','').strip()
        # client-side format already checked, but re-validate + dup check
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', new_email):
            error = 'enter a valid email address'
        elif Employer.objects.filter(email=new_email).exists():
            error = 'that email is already registered'
        else:
            # update session, new OTP
            otp = f"{random.randint(100000,999999):06d}"
            now_ts = timezone.now().timestamp()
            data['email'] = new_email
            data['otp'] = otp
            data['otp_sent_time'] = now_ts
            request.session['employer_signup_data'] = data

            # re-send email
            send_mail(
                "Your WorkWise Employer Verification Code",
                f"Hello {data['representative_name']},\nYour new code is {otp}\nIt expires in 15 minutes.",
                settings.EMAIL_HOST_USER,
                [new_email],
                fail_silently=False
            )
            return redirect('auth:verify_email_employer')

    # — Handle OTP verification —
    elif request.method == 'POST' and 'verify_submit' in request.POST:
        code = request.POST.get('verification_code','').strip()
        lat  = request.POST.get('latitude')
        lng  = request.POST.get('longitude')

        # TTL: 15 minutes
        if timezone.now().timestamp() - data['otp_sent_time'] > 900:
            return redirect('auth:signup_employer')

        if code != data.get('otp'):
            error = 'invalid verification code'
        else:
            # create Employer
            emp = Employer(
                company_name        = data['company_name'],
                representative_name = data['representative_name'],
                email               = data['email'],
                password            = data['password'],
                email_notify        = data['email_notify'],
                agree_terms         = data['agree_terms'],
                ip_address          = request.META.get('REMOTE_ADDR'),
                location            = {'lat': float(lat), 'lng': float(lng)} if lat and lng else None
            )
            emp.is_active = True
            emp.save()

            request.session.pop('employer_signup_data', None)
            return redirect(f"{reverse('auth:login')}?registered=1")

    # — Compute resend cooldown (30s) —
    now_ts     = timezone.now().timestamp()
    last_ts    = data.get('otp_sent_time', now_ts)
    elapsed    = now_ts - last_ts
    cooldown   = max(0, 30 - int(elapsed))

    return render(request, 'authentication/verify-email-employer.html', {
        'email': data['email'],
        'error': error,
        'modal_error': modal_error,
        'show_loc_prompt': show_loc_prompt,
        'resend_cooldown': cooldown,
    })



def resend_code_employer(request):
    data = request.session.get('employer_signup_data')
    if not data:
        return redirect('auth:signup_employer')

    now_ts = timezone.now().timestamp()
    # enforce 30s cooldown
    if now_ts - data.get('otp_sent_time', 0) < 30:
        return redirect('auth:verify_email_employer')

    # generate new OTP and update session
    otp = f"{random.randint(100000,999999):06d}"
    data['otp'] = otp
    data['otp_sent_time'] = now_ts
    request.session['employer_signup_data'] = data

    # send the new code
    send_mail(
        "Your WorkWise Employer Verification Code",
        f"Hello {data['representative_name']},\n\nYour new verification code is: {otp}\n\nIt will expire in 15 minutes.",
        settings.EMAIL_HOST_USER,
        [data['email']],
        fail_silently=False,
    )

    return redirect('auth:verify_email_employer')



def login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('candidate:dashboard')
    if request.session.get('employer_id'):
        return redirect(reverse('employer:dashboard'))
    elif request.session.get('candidate_id'):
        return redirect(reverse('candidate:dashboard'))
    
    error = None
    email = request.POST.get('email','').strip() if request.method=='POST' else ''
    registered = request.GET.get('registered') == '1'
    if request.method == 'POST':
        password     = request.POST.get('password','')
        account_type = request.POST.get('account_type','')

        # Validate inputs
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            error = 'enter a valid email address'
        elif not (6 <= len(password) <= 16):
            error = 'password must be 6–16 characters'
        elif account_type not in ('candidate','employer'):
            error = 'please select appropriate account type'
        else:
            # Lookup user
            Model = Candidate if account_type=='candidate' else Employer
            try:
                user = Model.objects.get(email=email, is_active=True, is_deleted=False)
            except Model.DoesNotExist:
                error = 'invalid credentials'
            else:
                if not check_password(password, user.password):
                    error = 'invalid credentials'
                else:
                    if Model == Employer:
                        request.session['employer_id'] = user.employer_id
                        return redirect(reverse('employer:dashboard'))
                    else:    
                        request.session['candidate_id'] = user.candidate_id
                        return redirect(next_url)

    return render(request, 'authentication/login.html', {
        'error': error,
        'email': email,
        'registered_success': registered,
        'next': next_url
    })




EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

def reset_password(request):
    errors = []
    form_data = request.session.get('pwd_reset', {'email':'','account_type':''})

    if request.method == 'POST' and 'send_otp' in request.POST:
        email = request.POST.get('email','').strip()
        acct  = request.POST.get('account_type','')

        # Server‐side validation
        if not EMAIL_RE.match(email):
            errors.append('enter a valid email address')
        if acct not in ('candidate','employer'):
            errors.append('please select appropriate account type!!')

        # Check user exists & is active/not deleted
        if not errors:
            Model = Candidate if acct=='candidate' else Employer
            if not Model.objects.filter(email=email, is_active=True, is_deleted=False).exists():
                errors.append('no active account found for that email')

        if not errors:
            # Generate OTP & stash
            otp = f"{random.randint(100000,999999):06d}"
            now_ts = timezone.now().timestamp()
            request.session['pwd_reset'] = {
                'email': email,
                'account_type': acct,
                'otp': otp,
                'otp_time': now_ts,
            }
            
            # Send OTP
            send_mail(
                "Your WorkWise Password Reset Code",
                f"Your code is: {otp}\nIt expires in 15 minutes.",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return redirect('auth:reset_password_verify')

        form_data = {'email': email, 'account_type': acct}

    return render(request, 'authentication/reset-password.html', {
        'errors': errors,
        'form_data': form_data,
    })


def reset_verify(request):
    data = request.session.get('pwd_reset')
    
    if not data or (timezone.now().timestamp() - data.get('otp_time', 0) > 900):
        request.session.pop('pwd_reset', None)
        return redirect('auth:reset_password')
    
    otp_error = None

    if request.method == 'POST' and 'verify_otp' in request.POST:
        code       = request.POST.get('verification_code','').strip()
        newpwd     = request.POST.get('new_password','')
        confirmpwd = request.POST.get('confirm_password','')

        # TTL check
        if timezone.now().timestamp() - data['otp_time'] > 900:
            request.session.pop('pwd_reset', None)
            return redirect('auth:reset_password')

        # Validation
        if code != data.get('otp'):
            otp_error = 'invalid verification code'
        elif not (6 <= len(newpwd) <= 16):
            otp_error = 'new password must be 6–16 characters'
        elif newpwd != confirmpwd:
            otp_error = 'passwords do not match'
        else:
            Model = Candidate if data['account_type']=='candidate' else Employer
            user = Model.objects.get(email=data['email'], is_active=True, is_deleted=False)
            user.password = make_password(newpwd)
            user.save()
            # cleanup & redirect with success flag
            request.session.pop('pwd_reset', None)
            
            return redirect(f"{reverse('auth:login')}?reset=1")

    return render(request, 'authentication/reset-password-verify.html', {
        'otp_error': otp_error,
        'form_data': data,
    })

