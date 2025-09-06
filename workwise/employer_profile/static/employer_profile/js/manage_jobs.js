// static/employer_profile/js/manage_jobs.js

document.addEventListener('DOMContentLoaded', () => {
  const searchInput  = document.getElementById('search-input');
  const filterStatus = document.getElementById('filter-status');
  const sortBy       = document.getElementById('sort-by');
  const container    = document.getElementById('jobs-container');
  const PAGE_SIZE    = 12;

  // 1) Load the full job list from the hidden JSON <script>
  const masterJobs = JSON.parse(
    document.getElementById('all-jobs-data').textContent
  );

  // 2) Define status ranking for primary sort
  const statusOrder = { active: 0, deactivated: 1, expired: 2 };

  // 3) Helper to grab CSRF token
  function getCookie(name) {
    let value = null;
    document.cookie.split(';').forEach(c => {
      const [k, v] = c.trim().split('=');
      if (k === name) value = decodeURIComponent(v);
    });
    return value;
  }

  // — Insert at the top, before buildCard() —
  function timeAgo(unixTs) {
    const now = Date.now();
    const diff = now - unixTs * 1000;   // in ms
    const mins = Math.floor(diff / 1000 / 60);
    const hrs  = Math.floor(mins / 60);
    const days = Math.floor(hrs / 24);

    if (days > 0) return `${days} day${days>1?'s':''}, ${hrs % 24}h ago`;
    if (hrs  > 0) return `${hrs} hour${hrs>1?'s':''}, ${mins % 60}m ago`;
    return `${mins} minute${mins>1?'s':''} ago`;
  }


  // 4) Build the exact same card HTML you have in your template
  function buildCard(job) {
      const postedAgo = timeAgo(job.posted_at_ts);

    return `
      <div class="job-card" data-status="${job.status}"
           data-posted="${job.posted_at_ts}"
           data-deadline="${job.application_deadline}">
        <div class="card-header">
          <h2 class="job-title">${job.title}</h2>
          <div class="job-tags">
            <span class="tag">${job.department}</span>
            <span class="tag">${job.work_type}</span>
            <span class="tag">${job.num_candidates_required} Vacancy${job.num_candidates_required>1?'ies':''}</span>
            <a href="/employer/jobs/${job.job_id}/applications/" style="text-decoration:none;">
              <span class="tag tag-apps">
                ${job.applications_count} Application${job.applications_count!==1?'s':''}
              </span>
            </a>
          </div>
        </div>
        <div class="card-body">
          <span class="badge status-${job.status}">
            ${job.status.charAt(0).toUpperCase() + job.status.slice(1)}
          </span>
          <div class="meta-line">
            
              <small class="meta-label">Posted:</small>
              <small class="meta-value">${postedAgo}</small>
            
          </div>
          <div class="meta-line">
            <small class="meta-label">Deadline:</small>
            <small class="meta-value">
              ${job.application_deadline}
              <span class="days-left">(${job.days_left} days left)</span>
            </small>
          </div>
        </div>
        <div class="card-actions">
          ${job.status==='active'
            ? `<a href="/employer/edit_job/${job.job_id}/" class="btn btn-edit">Edit</a>
               <form method="post" action="/employer/job_deactivate/${job.job_id}/"
                     class="deactivate-form" style="display:inline">
                 <input type="hidden" name="csrfmiddlewaretoken"
                        value="${getCookie('csrftoken')}">
                 <button type="submit" class="btn btn-deactivate">Deactivate</button>
               </form>`
            : `<button data-id="${job.job_id}" class="btn btn-duplicate">Duplicate</button>`
          }
        </div>
      </div>
    `;
  }

  // 5) Confirm‐deactivate modal logic (re-bound after each render)
  function bindModal() {
    const modal    = document.getElementById('confirm-modal');
    const btnYes   = document.getElementById('confirm-yes');
    const btnNo    = document.getElementById('confirm-no');
    let   formEl   = null;

    document.querySelectorAll('.deactivate-form button').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        formEl = btn.closest('form');
        modal.classList.add('active');
      });
    });

    btnNo.addEventListener('click', () => {
      modal.classList.remove('active');
      formEl = null;
    });

    btnYes.addEventListener('click', () => {
      if (formEl) formEl.submit();
    });
  }

  // 6) Main render: filter, sort, slice and inject
  function render() {
    // a) Copy the full list
    let list = masterJobs.slice();

    // b) Search by title
    const q = searchInput.value.trim().toLowerCase();
    if (q) {
      list = list.filter(j => j.title.toLowerCase().includes(q));
    }

    // c) Status filter
    const st = filterStatus.value;
    if (st) {
      list = list.filter(j => j.status === st);
    }

    // d) Sort by statusRank then key
    const [key, dirStr] = sortBy.value.split('_');
    const dir = dirStr === 'asc' ? 1 : -1;
    list.sort((a, b) => {
  const ra = statusOrder[a.status] ?? 3;
  const rb = statusOrder[b.status] ?? 3;
  if (ra !== rb) return ra - rb;

  const [key, dirStr] = sortBy.value.split('_');
  const dir = dirStr === 'asc' ? 1 : -1;

  let av, bv;
  if (key === 'posted') {
    av = a.posted_at_ts;
    bv = b.posted_at_ts;
  } else if (key === 'deadline') {
    av = new Date(a.application_deadline).getTime();
    bv = new Date(b.application_deadline).getTime();
  } else if (key === 'apps') {
    av = a.applications_count;
    bv = b.applications_count;
  }

  return (av - bv) * dir;
});

    // e) Show only the first PAGE_SIZE results
    const slice = list.slice(0, PAGE_SIZE);

    // f) Inject cards
    container.innerHTML = slice.map(buildCard).join('');

    // g) Re-bind modal handlers
    bindModal();
  }

  // 7) Wire up controls
  searchInput .addEventListener('input',  render);
  filterStatus.addEventListener('change', render);
  sortBy      .addEventListener('change', render);

  // 8) Initial draw
  render();
});
