document.addEventListener('DOMContentLoaded', function () {
    // Select all inputs with class 'phone-input'
    const phoneInputs = document.querySelectorAll('#phone-input')

    phoneInputs.forEach((phoneInput) => {
        // Set the maximum length attribute for the input
        phoneInput.setAttribute('maxlength', '16')

        phoneInput.addEventListener('input', function () {
            // Allow '+' at the start and numbers only
            this.value = this.value.replace(/(?!^\+)[^\d]/g, '')

            // Ensure '+' is at the start
            if (!this.value.startsWith('+')) {
                this.value = '+' + this.value.replace('+', '')
            }
        })
    })
})
