
// Helper to read CSRF cookie
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    document.cookie.split(';').forEach(c => {
      const [k, v] = c.trim().split('=');
      if (k === name) cookieValue = decodeURIComponent(v);
    });
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
  const depMap = window.DEP_MAP || {};
  let initialDepartment = window.initialDepartment || null;

  const skillsEl   = document.getElementById('skillsInput');
  const titleEl    = document.getElementById('jobTitleInput');
  const industryEl = document.getElementById('industrySelect');
  const deptEl     = document.getElementById('departmentSelect');
  const expEl      = document.getElementById('experienceInput');
  const btn        = document.getElementById('analyzeBtn');
  const form       = document.getElementById('skillGapForm');
  const loader     = document.getElementById('loader');
  const resultsEl  = document.getElementById('results');

  // Convert underscore-strings to human-readable form
  function humanize(str) {
    return str
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  // Populate department select based on chosen industry
  function populateDepts() {
    const list = depMap[industryEl.value] || [];
    deptEl.innerHTML = '<option value="">-- select department --</option>';
    list.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = humanize(d);
      deptEl.appendChild(opt);
    });
    if (initialDepartment) {
      deptEl.value = initialDepartment;
      initialDepartment = null;
    }
    validate();
  }

  industryEl.addEventListener('change', populateDepts);

  // Enable analyze button only when all fields are filled
  function validate() {
    const ok =
      skillsEl.value.trim() &&
      titleEl.value.trim() &&
      industryEl.value &&
      deptEl.value &&
      expEl.value !== '';
    btn.disabled = !ok;
  }
  [skillsEl, titleEl, industryEl, deptEl, expEl].forEach(el =>
    el.addEventListener('input', validate)
  );
  validate();

  // If an industry was pre-selected, populate departments immediately
  if (industryEl.value) populateDepts();

  // Handle form submission via AJAX
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    loader.classList.remove('hidden');
    resultsEl.innerHTML = '';

    const payload = {
      skills:     skillsEl.value.split(',').map(s => s.trim()).filter(s => s),
      job_title:  titleEl.value.trim(),
      industry:   industryEl.value,
      department: deptEl.value,
      experience: Number(expEl.value)
    };

    try {
      const res = await fetch(form.action || window.location.href, {
        method: 'POST',
        headers: {
          'Content-Type':     'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken':      csrftoken,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (data.error) {
        // Display error from server
        resultsEl.textContent = data.error;
      } else {
        // Render each skill's guidance
        data.suggestions.forEach(entry => {
          const box = document.createElement('div');
          box.className = 'suggestion-box';
          box.innerHTML = `
            <h4>Skill: ${entry.skill}</h4>
            <p>${entry.guidance}</p>
          `;
          resultsEl.appendChild(box);
        });
      }
    } catch (err) {
      console.error(err);
      resultsEl.textContent = 'Error fetching guidance. Please try again.';
    } finally {
      loader.classList.add('hidden');
    }
  });
});
