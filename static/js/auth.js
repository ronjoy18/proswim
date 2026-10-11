/**
 * Password validation engine.
 * Ensures rules update live while preserving inputs during validation errors.
 */

document.addEventListener("DOMContentLoaded", () => {
  const passwordField = document.getElementById("auth-password");
  const passwordConfirmField = document.getElementById("auth-password-confirm");
  
  const rules = {
    length: { regex: /.{8,}/, element: document.getElementById("rule-len") },
    upper: { regex: /[A-Z]/, element: document.getElementById("rule-up") },
    lower: { regex: /[a-z]/, element: document.getElementById("rule-low") },
    number: { regex: /[0-9]/, element: document.getElementById("rule-num") },
    special: { regex: /[^A-Za-z0-9]/, element: document.getElementById("rule-spc") },
  };

  if (passwordField) {
    passwordField.addEventListener("input", () => {
      const val = passwordField.value;
      for (const [key, rule] of Object.entries(rules)) {
        if (!rule.element) continue;
        if (rule.regex.test(val)) {
          rule.element.classList.remove("invalid");
          rule.element.classList.add("valid");
        } else {
          rule.element.classList.remove("valid");
          rule.element.classList.add("invalid");
        }
      }
    });
  }

  // Preserve Form State on Submission via AJAX
  const registerForm = document.getElementById("registration-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const feedbackBox = document.getElementById("form-feedback");
      feedbackBox.style.display = "none";
      feedbackBox.className = "";

      const formData = new FormData(registerForm);
      const payload = Object.fromEntries(formData.entries());

      try {
        const response = await fetch("/api/v1/auth/register/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
          },
          body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
          feedbackBox.textContent = "Profile registered successfully. Establishing session...";
          feedbackBox.className = "alert-success";
          feedbackBox.style.display = "block";
          setTimeout(() => {
            window.location.href = "/auth/?mode=login";
          }, 1500);
        } else {
          // Failure: Preserves form inputs, including password fields
          let errors = [];
          for (const [field, messages] of Object.entries(data)) {
            errors.push(`${field.toUpperCase()}: ${Array.isArray(messages) ? messages.join(" ") : messages}`);
          }
          feedbackBox.textContent = errors.join(" | ");
          feedbackBox.className = "alert-error";
          feedbackBox.style.display = "block";
          // Inputs remain untouched; user does not have to retype their password
        }
      } catch (err) {
        feedbackBox.textContent = "Fatal execution fault. Verify local service gateway.";
        feedbackBox.className = "alert-error";
        feedbackBox.style.display = "block";
      }
    });
  }
});

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

