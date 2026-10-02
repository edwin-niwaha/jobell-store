(function () {
  const forms = document.querySelectorAll("[data-newsletter-form]");

  forms.forEach((form) => {
    const emailInput = form.querySelector('input[type="email"]');
    const submitButton = form.querySelector('button[type="submit"]');

    if (emailInput) {
      emailInput.addEventListener("blur", () => {
        emailInput.value = emailInput.value.trim().toLowerCase();
      });
    }

    form.addEventListener("submit", () => {
      if (emailInput) {
        emailInput.value = emailInput.value.trim().toLowerCase();
      }

      if (submitButton && form.checkValidity()) {
        submitButton.disabled = true;
        submitButton.dataset.originalText = submitButton.textContent;
        submitButton.textContent = "Subscribing...";
      }
    });
  });
})();
