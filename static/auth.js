// AUTH JAVASCRIPT
document.addEventListener('DOMContentLoaded', () => {
    // Login Form Handler
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Signup Form Handler
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);

        // Password strength checker
        const passwordInput = document.getElementById('password');
        if (passwordInput) {
            passwordInput.addEventListener('input', checkPasswordStrength);
        }
    }

    // Forgot Password Modal
    const forgotLink = document.getElementById('forgotPasswordLink');
    const modal = document.getElementById('forgotPasswordModal');
    const closeModal = document.getElementById('closeModal');
    const forgotForm = document.getElementById('forgotPasswordForm');

    if (forgotLink && modal) {
        forgotLink.addEventListener('click', (e) => {
            e.preventDefault();
            modal.style.display = 'flex';
        });

        closeModal.addEventListener('click', () => {
            modal.style.display = 'none';
            document.getElementById('forgotError').style.display = 'none';
            document.getElementById('forgotSuccess').style.display = 'none';
            document.getElementById('forgotEmail').value = '';
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });

        forgotForm.addEventListener('submit', handleForgotPassword);
    }
});

// Login Handler
async function handleLogin(e) {
    e.preventDefault();
    
    const btn = document.getElementById('loginBtn');
    const errorMsg = document.getElementById('errorMessage');
    
    // Get form data
    const formData = new FormData(e.target);
    const email = formData.get('email');
    const password = formData.get('password');
    const remember = formData.get('remember') === 'on';
    
    // Disable button
    btn.disabled = true;
    btn.innerHTML = '<span>Signing in...</span>';
    
    try {
        // TODO: Replace with your actual API endpoint
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password, remember })
        });
        
        if (!response.ok) {
            throw new Error('Invalid credentials');
        }
        
        const data = await response.json();
        
        // Store token
        if (remember) {
            localStorage.setItem('authToken', data.token);
        } else {
            sessionStorage.setItem('authToken', data.token);
        }
        
        // Redirect to dashboard
        window.location.href = '/app';
        
    } catch (error) {
        errorMsg.textContent = error.message || 'Login failed. Please try again.';
        errorMsg.style.display = 'block';
        
        btn.disabled = false;
        btn.innerHTML = '<span>Sign In</span><span class="btn-arrow">→</span>';
    }
}

// Signup Handler
async function handleSignup(e) {
    e.preventDefault();
    
    const btn = document.getElementById('signupBtn');
    const errorMsg = document.getElementById('errorMessage');
    
    // Get form data
    const formData = new FormData(e.target);
    const name = formData.get('name');
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const terms = formData.get('terms') === 'on';
    
    // Validation
    if (password !== confirmPassword) {
        errorMsg.textContent = 'Passwords do not match';
        errorMsg.style.display = 'block';
        return;
    }
    
    if (password.length < 8) {
        errorMsg.textContent = 'Password must be at least 8 characters';
        errorMsg.style.display = 'block';
        return;
    }
    
    if (!terms) {
        errorMsg.textContent = 'You must agree to the Terms of Service';
        errorMsg.style.display = 'block';
        return;
    }
    
    // Disable button
    btn.disabled = true;
    btn.innerHTML = '<span>Creating account...</span>';
    
    try {
        // TODO: Replace with your actual API endpoint
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, email, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Signup failed');
        }
        
        const data = await response.json();
        
        // Store token
        localStorage.setItem('authToken', data.token);
        
        // Redirect to dashboard
        window.location.href = '/app';
        
    } catch (error) {
        errorMsg.textContent = error.message || 'Signup failed. Please try again.';
        errorMsg.style.display = 'block';
        
        btn.disabled = false;
        btn.innerHTML = '<span>Create Account</span><span class="btn-arrow">→</span>';
    }
}

// Password Strength Checker
function checkPasswordStrength() {
    const password = document.getElementById('password').value;
    const strengthBar = document.getElementById('passwordStrength');
    
    if (!strengthBar) return;
    
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]+/)) strength++;
    if (password.match(/[A-Z]+/)) strength++;
    if (password.match(/[0-9]+/)) strength++;
    if (password.match(/[$@#&!]+/)) strength++;
    
    strengthBar.className = 'password-strength';
    
    if (strength <= 2) {
        strengthBar.classList.add('weak');
    } else if (strength <= 4) {
        strengthBar.classList.add('medium');
    } else {
        strengthBar.classList.add('strong');
    }
}

// IMPROVED: Toggle password visibility for individual input
function togglePassword(event) {
    // Get the button that was clicked
    const button = event.currentTarget || event.target;
    
    // Find the input field (sibling of the button)
    const inputWrapper = button.parentElement;
    const input = inputWrapper.querySelector('input[type="password"], input[type="text"]');
    
    if (!input) return;
    
    // Toggle input type
    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '🙈'; // Changed eye icon
    } else {
        input.type = 'password';
        button.textContent = '👁️'; // Original eye icon
    }
}

// Forgot Password Handler
async function handleForgotPassword(e) {
    e.preventDefault();

    const btn = document.getElementById('forgotBtn');
    const errorMsg = document.getElementById('forgotError');
    const successMsg = document.getElementById('forgotSuccess');
    const email = document.getElementById('forgotEmail').value.trim();

    errorMsg.style.display = 'none';
    successMsg.style.display = 'none';

    btn.disabled = true;
    btn.innerHTML = '<span>Sending...</span>';

    try {
        const response = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to send reset link');
        }

        successMsg.textContent = data.message || 'If that email is registered, a reset link has been sent.';
        successMsg.style.display = 'block';
        document.getElementById('forgotEmail').value = '';

    } catch (error) {
        errorMsg.textContent = error.message || 'Something went wrong. Please try again.';
        errorMsg.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Send Reset Link</span><span class="btn-arrow">→</span>';
    }
}

// Check if user is already logged in
function checkAuth() {
    const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    
    if (token && (window.location.pathname.includes('login.html') || window.location.pathname.includes('signup.html'))) {
        window.location.href = '/app';
    }
}

checkAuth();