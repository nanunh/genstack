// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get the login form if it exists on the page
    const loginForm = document.querySelector('form');
    
    if (loginForm) {
        // Add form validation
        loginForm.addEventListener('submit', function(event) {
            const emailInput = document.getElementById('email');
            const passwordInput = document.getElementById('password');
            
            let isValid = true;
            
            // Simple email validation
            if (!emailInput.value || !emailInput.value.includes('@')) {
                isValid = false;
                highlightError(emailInput, 'Please enter a valid email address');
            } else {
                removeError(emailInput);
            }
            
            // Password validation (at least 6 characters)
            if (!passwordInput.value || passwordInput.value.length < 6) {
                isValid = false;
                highlightError(passwordInput, 'Password must be at least 6 characters');
            } else {
                removeError(passwordInput);
            }
            
            // Prevent form submission if validation fails
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
    
    // Function to highlight input errors
    function highlightError(inputElement, message) {
        inputElement.style.borderColor = '#c62828';
        
        // Check if error message already exists
        let errorSpan = inputElement.parentElement.querySelector('.input-error');
        
        if (!errorSpan) {
            errorSpan = document.createElement('span');
            errorSpan.className = 'input-error';
            errorSpan.style.color = '#c62828';
            errorSpan.style.fontSize = '14px';
            errorSpan.style.display = 'block';
            errorSpan.style.marginTop = '5px';
            inputElement.parentElement.appendChild(errorSpan);
        }
        
        errorSpan.textContent = message;
    }
    
    // Function to remove error highlighting
    function removeError(inputElement) {
        inputElement.style.borderColor = '#ddd';
        
        const errorSpan = inputElement.parentElement.querySelector('.input-error');
        if (errorSpan) {
            errorSpan.remove();
        }
    }
    
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelector('.flash-messages');
    if (flashMessages) {
        setTimeout(function() {
            flashMessages.style.opacity = '0';
            flashMessages.style.transition = 'opacity 1s';
            
            // Remove from DOM after fade out
            setTimeout(function() {
                flashMessages.remove();
            }, 1000);
        }, 5000);
    }
});
