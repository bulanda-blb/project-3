# employer_profile/utils/ranking.py

import datetime
from math import radians, sin, cos, sqrt, atan2

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from candidate_profile.models import CandidateCV  # adjust import if needed

# === WEIGHTS (no recency) ===
W_REQ    = 0.20   # requirements match
W_PREF   = 0.25   # preferred skills
W_CORE   = 0.10   # core skills overlap
W_EXP    = 0.05   # experience fit
W_EDU    = 0.10   # education level
W_CERT   = 0.02   # certifications
W_LANG   = 0.03   # languages
W_PROJ   = 0.05   # project alignment
W_TEXT   = 0.15   # TF-IDF semantic similarity
W_GEO    = 0.05   # geographic proximity

D_MAX = 200.0  # km for full geo score

EDU_LEVELS = {
    'high school': 1,
    'bachelor':    2,
    'master':      3,
    'phd':         4
}


def haversine(loc1, loc2):
    """Return distance in km between two {'lat','lng'} dicts."""
    lat1, lng1 = loc1.get('lat'), loc1.get('lng')
    lat2, lng2 = loc2.get('lat'), loc2.get('lng')
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return D_MAX  # treat missing as far away
    R = 6371.0
    rlat1, rlng1 = radians(lat1), radians(lng1)
    rlat2, rlng2 = radians(lat2), radians(lng2)
    dlat, dlng = rlat2 - rlat1, rlng2 - rlng1
    a = sin(dlat/2)**2 + cos(rlat1)*cos(rlat2)*sin(dlng/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def _skill_score(cand_items, job_items):
    # both inputs lists; filter to real str
    cand = [str(i).strip().lower() for i in (cand_items or []) if i]
    job  = [str(i).strip().lower() for i in (job_items or [])  if i]
    if not job:
        return 0.0
    return len(set(cand) & set(job)) / len(job)


def _exp_score(cand_exp, exp_min, exp_max):
    try:
        ce = float(cand_exp or 0)
    except:
        return 0.0
    if exp_min <= ce <= exp_max:
        return 1.0
    diff = min(abs(ce - exp_min), abs(ce - exp_max))
    return max(0.0, 1 - diff/2)


def _edu_score(cand_eds, job_level):
    cand_lvls = [EDU_LEVELS.get(str(e).lower(), 0) for e in (cand_eds or []) if e]
    cand_lvl  = max(cand_lvls, default=0)
    job_lvl   = EDU_LEVELS.get(str(job_level or '').lower(), 0)
    if job_lvl == 0:
        return 0.0
    return 1.0 if cand_lvl >= job_lvl else cand_lvl / job_lvl


def _cert_score(cand_certs, job_reqs):
    cand = [str(c).strip().lower() for c in (cand_certs or []) if c]
    job  = [str(r).strip().lower() for r in (job_reqs or [])  if r]
    if not cand:
        return 0.0
    return len(set(cand) & set(job)) / len(cand)


def _lang_score(cand_langs, job_langs):
    cand = [str(l).strip().lower() for l in (cand_langs or []) if l]
    job  = [str(l).strip().lower() for l in (job_langs or [])  if l]
    if not job:
        return 0.0
    return len(set(cand) & set(job)) / len(job)


def _proj_score(projects, job_text):
    best = 0.0
    jt   = job_text.lower()
    for p in (projects or []):
        name = str(p.get('name') or '').strip()
        desc = str(p.get('description') or '').strip()
        if not (name or desc):
            continue
        txt = f"{name} {desc}".lower()
        score = fuzz.token_sort_ratio(txt, jt) / 100
        best = max(best, score)
    return best


def _compute_text_sims(job_text, cand_texts):
    # filter out empties
    corpus = [job_text] + [t for t in cand_texts if t]
    if len(corpus) < 2:
        return [0.0] * len(cand_texts)
    vec   = TfidfVectorizer(stop_words='english').fit(corpus)
    tfidf = vec.transform(corpus)
    job_vec = tfidf[0]
    sims    = cosine_similarity(job_vec, tfidf[1:])[0]
    # if some cand_texts were empty, pad with zeros
    return list(sims) + [0.0] * (len(cand_texts) - len(sims))


def rank_applications(job, applications):
    """
    Return applications sorted by our hybrid ranking.
    """

    # 1) Load latest CV parsed_data for each candidate
    ids = [app.candidate.candidate_id for app in applications]
    cvs = CandidateCV.objects.filter(
        candidate__candidate_id__in=ids
    ).order_by('candidate__candidate_id', '-parsed_at')

    cv_map = {}
    for cv in cvs:
        cid = cv.candidate.candidate_id
        if cid not in cv_map:
            cv_map[cid] = cv.parsed_data or {}

    # 2) Prepare job data
    job_reqs    = job.requirements or []
    pref_skills = job.preferred_skills or []
    core_pool   = list(set(job_reqs) | set(pref_skills))
    job_langs   = job.languages or []
    job_loc     = job.map_location or {}
    jt_parts    = [
        str(job.title or ''),
        str(job.description or ''),
        *[str(r) for r in job_reqs],
        *[str(s) for s in pref_skills],
        *[str(l) for l in job_langs],
    ]
    job_text = " ".join([p for p in jt_parts if p]).lower()

    # 3) Build CV text blobs
    cand_texts = []
    for app in applications:
        pd = cv_map.get(app.candidate.candidate_id, {})
        parts = [
            str(pd.get('summary','') or ''),
            " ".join([str(e) for e in (pd.get('experience') or []) if e]),
            " ".join([str(s) for s in (pd.get('skills') or [])     if s]),
            " ".join([str(c) for c in (pd.get('certifications') or []) if c]),
        ]
        txt = " ".join([p for p in parts if p]).lower()
        cand_texts.append(txt)

    text_sims = _compute_text_sims(job_text, cand_texts)

    # 4) Score each application
    scored = []
    for idx, app in enumerate(applications):
        pd    = cv_map.get(app.candidate.candidate_id, {})

        cs    = pd.get('skills', [])
        ce    = pd.get('experience_years', 0)
        ced   = pd.get('education', [])
        certs = pd.get('certifications', [])
        langs = pd.get('languages', [])
        projs = pd.get('projects', [])
        # pd.get('map_location') might also drive geo if available

        s_req  = _skill_score(cs + ced + certs, job_reqs)
        s_pref = _skill_score(cs, pref_skills)
        s_core = _skill_score(cs, core_pool)
        s_exp  = _exp_score(ce, job.experience_min, job.experience_max)
        s_edu  = _edu_score(ced, job.experience_level)
        s_cert = _cert_score(certs, job_reqs)
        s_lang = _lang_score(langs, job_langs)
        s_proj = _proj_score(projs, job_text)
        s_text = text_sims[idx]

        # Geo
        try:
            dist  = haversine(job_loc, pd.get('map_location') or {})
            s_geo = max(0.0, 1 - dist / D_MAX)
        except:
            s_geo = 0.0

        final = (
            W_REQ   * s_req  +
            W_PREF  * s_pref +
            W_CORE  * s_core +
            W_EXP   * s_exp  +
            W_EDU   * s_edu  +
            W_CERT  * s_cert +
            W_LANG  * s_lang +
            W_PROJ  * s_proj +
            W_TEXT  * s_text +
            W_GEO   * s_geo
        )

        scored.append((final, app))
        for final, app in scored:
             print(app.candidate.email, round(final,3))

    # 5) Sort by descending score, tie-break newest
    scored.sort(key=lambda x: (x[0], x[1].applied_at), reverse=True)
    return [app for _, app in scored]

