document.addEventListener('DOMContentLoaded', () => {
  // —— Helpers —— 
  function showError(el, msg) {
    el.classList.add('error');
    const err = document.getElementById(`error-${el.name}`);
    if (err) err.textContent = msg;
  }
  function clearError(el) {
    el.classList.remove('error');
    const err = document.getElementById(`error-${el.name}`);
    if (err) err.textContent = '';
  }
  function clearErrors(container) {
    container.querySelectorAll('.error-text').forEach(e => e.textContent = '');
    container.querySelectorAll('input, select').forEach(i => i.classList.remove('error'));
  }

  // —— Modal Open/Close —— 
  document.querySelectorAll('[data-modal]').forEach(btn => {
    const m = btn.dataset.modal;
    const modal = document.getElementById(m);
    if (!modal) return;
    btn.addEventListener('click', () => modal.classList.add('active'));
  });
  document.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal');
      modal.classList.remove('active');
      clearErrors(modal);
    });
  });

  // —— Top Section (Company & Email) —— 
  const formTop = document.getElementById('form-edit-top');
  if (formTop) {
    const fldName  = formTop.querySelector('[name="company_name"]');
    const fldEmail = formTop.querySelector('[name="email"]');
    const btnTop   = formTop.querySelector('.btn-save');

    function validateTop() {
      let ok = true;
      const name  = fldName.value.trim();
      const email = fldEmail.value.trim();
      // Name
      if (!name) {
        showError(fldName, 'Required.');
        ok = false;
      } else if (name.length > 150) {
        showError(fldName, 'Max 150 characters.');
        ok = false;
      } else clearError(fldName);
      // Email
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!email) {
        showError(fldEmail, 'Required.');
        ok = false;
      } else if (!re.test(email)) {
        showError(fldEmail, 'Invalid email.');
        ok = false;
      } else clearError(fldEmail);
      btnTop.disabled = !ok;
    }

    [fldName, fldEmail].forEach(f => f.addEventListener('input', validateTop));
    validateTop();
  }

  // —— Logo Upload —— 
  const formLogo    = document.getElementById('form-logo');
  if (formLogo) {
    const inputLogo   = document.getElementById('modal-logo-input');
    const previewLogo = document.getElementById('preview-logo');
    const btnLogoSave = formLogo.querySelector('.btn-save');
    const errLogo     = document.getElementById('error-logo');

    inputLogo.addEventListener('change', () => {
      errLogo.textContent = '';
      btnLogoSave.disabled = true;
      const file = inputLogo.files[0];
      if (!file) return;
      if (!/^image\/(jpeg|png)$/.test(file.type)) {
        errLogo.textContent = 'Only JPEG or PNG allowed.';
        return;
      }
      if (file.size > 2*1024*1024) {
        errLogo.textContent = 'Max 2 MB.';
        return;
      }
      previewLogo.src = URL.createObjectURL(file);
      btnLogoSave.disabled = false;
    });
  }

    // —— Certificate Upload & Preview —— 
  const formVerify = document.getElementById('form-verify');
  if (formVerify) {
    const inputCert   = document.getElementById('modal-cert');
    const previewCert = document.getElementById('preview-cert');
    const btnVerify   = formVerify.querySelector('.btn-save');
    const errCert     = document.getElementById('error-certificate');

    inputCert.addEventListener('change', () => {
      errCert.textContent = '';
      btnVerify.disabled = true;
      const file = inputCert.files[0];
      if (!file) return;

      // Only accept image or PDF
      if (!/^image\/|^application\/pdf/.test(file.type)) {
        errCert.textContent = 'Only JPEG, PNG, or PDF allowed.';
        return;
      }
      // Max 2 MB
      if (file.size > 2*1024*1024) {
        errCert.textContent = 'Max file size is 2 MB.';
        return;
      }

      // Preview: if image, show thumbnail; if PDF, use placeholder icon
      if (file.type.startsWith('image/')) {
        previewCert.src = URL.createObjectURL(file);
      } else {
        previewCert.src = 'https://cdn-icons-png.flaticon.com/512/337/337946.png';
      }

      btnVerify.disabled = false;
    });
  }




  // —— Password Change —— 
  const formPw = document.getElementById('form-password');
  if (formPw) {
    const fldOld  = formPw.querySelector('[name="old_password"]');
    const fldNew  = formPw.querySelector('[name="new_password"]');
    const fldConf = formPw.querySelector('[name="confirm_password"]');
    const btnPw   = formPw.querySelector('.btn-save');
    const pwRe    = /^(?=.*\d)(?=.*[^\w\s]).{6,16}$/;

    function validatePw() {
      let ok = true;
      const vOld  = fldOld.value.trim();
      const vNew  = fldNew.value.trim();
      const vConf = fldConf.value.trim();

      if (!vOld) {
        showError(fldOld, 'Required.');
        ok = false;
      } else clearError(fldOld);

      if (!vNew) {
        showError(fldNew, 'Required.');
        ok = false;
      } else if (!pwRe.test(vNew)) {
        showError(fldNew, '6–16 chars, include number & special.');
        ok = false;
      } else clearError(fldNew);

      if (!vConf) {
        showError(fldConf, 'Required.');
        ok = false;
      } else if (vConf !== vNew) {
        showError(fldConf, 'Does not match.');
        ok = false;
      } else clearError(fldConf);

      btnPw.disabled = !ok;
    }

    [fldOld, fldNew, fldConf].forEach(f => {
      f.addEventListener('input', validatePw);
      f.addEventListener('blur', validatePw);
    });
    validatePw();
  }

  // —— Details Form —— 
const displayDiv  = document.querySelector('.details-display');
const formDetails = document.getElementById('form-details');

if (formDetails) {
  const btnEdit    = document.getElementById('btn-edit-details');
  const btnCancel  = document.querySelector('.btn-cancel-details');
  const btnDetails = document.getElementById('btn-save-details');
  const fields     = Array.from(formDetails.querySelectorAll('input,select,textarea'));

  // Toggle display ↔ edit
  if (btnEdit) {
    btnEdit.addEventListener('click', () => {
      displayDiv.style.display = 'none';
      formDetails.style.display = 'block';
      validateDetails();
    });
  }
  if (btnCancel) {
    btnCancel.addEventListener('click', () => {
      formDetails.style.display = 'none';
      displayDiv.style.display  = 'block';
    });
  }

  // Custom rules
  const validators = {
    company_size: v => !!v || 'Required.',
    founded_date: v => {
      if (!v) return 'Required.';
      const d = new Date(v);
      return d <= new Date() || 'Cannot be in the future.';
    },
    phone_number: v => /^\d{10,15}$/.test(v) || 'Must be 10–15 digits.',
    address:      v => !!v || 'Required.',
    website:      v => !v || /^https?:\/\//.test(v) || 'Must start with http:// or https://',
    facebook:     v => !v || /^https?:\/\//.test(v) || 'Must start with http:// or https://',
    linkedin:     v => !v || /^https?:\/\//.test(v) || 'Must start with http:// or https://',
    description: v => (v.length >= 20) || 'At least 20 characters.',

  };

  // Validate a single field
  function validateField(fld) {
    const v = fld.value.trim();
    let err = '';

    // HTML5 built-in
    if (!fld.checkValidity()) {
      err = fld.validationMessage;
    }
    // custom rule if present
    else if (validators[fld.name]) {
      const res = validators[fld.name](v);
      if (res !== true) err = res;
    }

    if (err) showError(fld, err);
    else    clearError(fld);
  }

  // Validate all fields & toggle button
  function validateDetails() {
    let ok = true;
    fields.forEach(fld => {
      validateField(fld);
      if (fld.classList.contains('error')) ok = false;
    });
    btnDetails.disabled = !ok;
  }

  // Attach events
  fields.forEach(fld => {
    fld.addEventListener('input', validateDetails);
    fld.addEventListener('change', validateDetails);
    fld.addEventListener('blur', () => validateField(fld));
  });

  // Initial check
  validateDetails();
}

// —— Email Notify Toggle —— 
const toggle = document.getElementById('toggle-notify');
if (toggle && window.toggleNotifyUrl) {
  toggle.addEventListener('change', () => {
    const desired = toggle.checked;
    fetch(window.toggleNotifyUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ email_notify: desired }),
    })
    .then(r => r.json())
    .then(data => {
      if (!data.success) {
        // revert on error
        toggle.checked = !desired;
        alert(data.error || 'Could not update setting');
      }
    })
    .catch(() => {
      toggle.checked = !desired;
      alert('Network error');
    });
  });
}


 
});
