// Authentication page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = this.querySelectorAll('input[required]');
            let isValid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = '#f44336';
                } else {
                    input.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showNotification('Please fill in all required fields', true);
            }
        });
    });
    
    // Password strength indicator for registration
    const passwordInput = document.querySelector('input[name="password1"]');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const strength = checkPasswordStrength(this.value);
            updatePasswordStrength(strength);
        });
    }
    
    // Password confirmation check
    const password2Input = document.querySelector('input[name="password2"]');
    if (password2Input && passwordInput) {
        password2Input.addEventListener('input', function() {
            if (this.value !== passwordInput.value) {
                this.style.borderColor = '#f44336';
            } else {
                this.style.borderColor = '';
            }
        });
    }
});

function checkPasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
}

function updatePasswordStrength(score) {
    const indicator = document.getElementById('password-strength');
    if (!indicator) return;
    
    const texts = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const colors = ['#f44336', '#ff9800', '#ffeb3b', '#8bc34a', '#4caf50'];
    
    indicator.textContent = texts[score - 1] || 'Very Weak';
    indicator.style.color = colors[score - 1] || '#f44336';
}