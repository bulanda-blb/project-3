
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("candidate-signup-form");
    const firstName = form.querySelector("input[name='first_name']");
    const lastName = form.querySelector("input[name='last_name']");
    const email = form.querySelector("input[name='email']");
    const password = form.querySelector("input[name='password']");
    const confirmPassword = form.querySelector("input[name='confirm_password']");
    const agreeTerms = form.querySelector("input[name='agree_terms']");
    const submitBtn = form.querySelector("button[type='submit']");
    const errorDisplay = document.getElementById("form-error-message");

    // Regex Patterns
    const nameRegex = /^[A-Za-z]+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const passwordRegex = /^(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{6,16}$/;

    // Track touched fields
    const touched = {
        first_name: false,
        last_name: false,
        email: false,
        password: false,
        confirm_password: false,
        agree_terms: false
    };

    function validate() {
        const errors = [];

        // Validate only after field is touched
        if (touched.first_name && !nameRegex.test(firstName.value.trim())) {
            errors.push("first name must contain only letters");
        }
        if (touched.last_name && !nameRegex.test(lastName.value.trim())) {
            errors.push("last name must contain only letters");
        }
        if (touched.email && !emailRegex.test(email.value.trim())) {
            errors.push("enter a valid email address");
        }
        if (touched.password && !passwordRegex.test(password.value)) {
            errors.push("password must be 6–16 chars with at least one number & special character");
        }
        if (touched.confirm_password && password.value !== confirmPassword.value) {
            errors.push("passwords do not match");
        }
        if (touched.agree_terms && !agreeTerms.checked) {
            errors.push("you must agree to the terms and conditions");
        }

        // Show first error or clear
        errorDisplay.textContent = errors[0] || "";

        // Check if all are valid to enable submit
        const allValid =
            nameRegex.test(firstName.value.trim()) &&
            nameRegex.test(lastName.value.trim()) &&
            emailRegex.test(email.value.trim()) &&
            passwordRegex.test(password.value) &&
            password.value === confirmPassword.value &&
            agreeTerms.checked;

        submitBtn.disabled = !allValid;
        submitBtn.style.opacity = allValid ? "1" : "0.5";
    }

    // Mark fields as touched on blur, then validate
    [firstName, lastName, email, password, confirmPassword, agreeTerms].forEach(input => {
        input.addEventListener("blur", () => {
            touched[input.name] = true;
            validate();
        });
        input.addEventListener("input", () => {
            if (touched[input.name]) validate();
        });
        if (input.type === "checkbox") {
            input.addEventListener("change", () => {
                touched[input.name] = true;
                validate();
            });
        }
    });

    // Initial state
    submitBtn.disabled = true;
    submitBtn.style.opacity = "0.5";
});

