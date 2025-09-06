// static/candidate_profile/js/profile.js

// Utility to read a cookie (for CSRF)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    document.cookie.split(';').forEach(cookie => {
      const [key, val] = cookie.trim().split('=');
      if (key === name) cookieValue = decodeURIComponent(val);
    });
  }
  return cookieValue;
}

document.addEventListener('DOMContentLoaded', () => {
  // ----- Modal Open / Close -----
  document.querySelectorAll('[data-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById(btn.dataset.modal).style.display = 'flex';
    });
  });
  document.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal').style.display = 'none';
    });
  });

  // ----- Email Notify Toggle (AJAX) -----
  const toggle = document.getElementById('toggle-notify');
  if (toggle) {
    toggle.addEventListener('change', () => {
      fetch('/candidate/toggle-notify/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      }).catch(() => {
        alert('Could not update notification setting.');
      });
    });
  }

  // ----- Real-time Validation: Name / Email Form -----
  const fnIn    = document.getElementById('input-first-name');
  const lnIn    = document.getElementById('input-last-name');
  const emIn    = document.getElementById('input-email');
  const saveTop = document.getElementById('save-top-btn');
  const nameRe  = /^[A-Za-z]+$/;
  function validateTop() {
    let valid = true;
    // First Name
    if (!nameRe.test(fnIn.value.trim())) {
      document.getElementById('error-first-name').textContent = 'Letters only.';
      valid = false;
    } else {
      document.getElementById('error-first-name').textContent = '';
    }
    // Last Name
    if (!nameRe.test(lnIn.value.trim())) {
      document.getElementById('error-last-name').textContent = 'Letters only.';
      valid = false;
    } else {
      document.getElementById('error-last-name').textContent = '';
    }
    // Email
    if (!/^\S+@\S+\.\S+$/.test(emIn.value.trim())) {
      document.getElementById('error-email').textContent = 'Invalid email format.';
      valid = false;
    } else {
      document.getElementById('error-email').textContent = '';
    }
    saveTop.disabled = !valid;
    saveTop.classList.toggle('disabled', !valid);
  }
  [fnIn, lnIn, emIn].forEach(i => i.addEventListener('input', validateTop));
  validateTop();

  // ----- Real-time Validation: Profile Picture Form -----
  const picIn   = document.getElementById('input-picture');
  const savePic = document.getElementById('save-pic-btn');
  function validatePic() {
    const f = picIn.files[0];
    let valid = false, msg = '';
    if (!f) {
      msg = 'Please select an image.';
    } else if (f.size > 2 * 1024 * 1024) {
      msg = 'File must be under 2 MB.';
    } else if (!['image/jpeg','image/png'].includes(f.type)) {
      msg = 'Only PNG or JPEG allowed.';
    } else {
      valid = true;
    }
    document.getElementById('error-picture').textContent = msg;
    savePic.disabled = !valid;
    savePic.classList.toggle('disabled', !valid);
  }
  picIn.addEventListener('change', validatePic);
  validatePic();

  // ----- Real-time Validation: Password Form -----
  const oldPw = document.getElementById('old-password');
  const newPw = document.getElementById('new-password');
  const cfPw  = document.getElementById('confirm-password');
  const savePw= document.getElementById('save-password-btn');
  const pwRe   = /^(?=.*\d)(?=.*[^A-Za-z0-9]).{6,16}$/;
  function validatePw() {
    let valid = true;
    // Old Password
    if (!oldPw.value.trim()) {
      document.getElementById('error-old-password').textContent = 'Current password required.';
      valid = false;
    } else {
      document.getElementById('error-old-password').textContent = '';
    }
    // New Password complexity
    if (!pwRe.test(newPw.value)) {
      document.getElementById('error-new-password').textContent =
        '6–16 chars, include 1 digit & 1 special char.';
      valid = false;
    } else {
      document.getElementById('error-new-password').textContent = '';
    }
    // Confirm matches
    if (newPw.value !== cfPw.value) {
      document.getElementById('error-confirm-password').textContent = 'Passwords must match.';
      valid = false;
    } else {
      document.getElementById('error-confirm-password').textContent = '';
    }
    savePw.disabled = !valid;
    savePw.classList.toggle('disabled', !valid);
  }
  [oldPw, newPw, cfPw].forEach(i => i.addEventListener('input', validatePw));
  validatePw();
});
