// Add CSRF token to all AJAX requests
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (csrfToken) {
        // Add CSRF token to AJAX requests
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            // Only add for POST requests to our own server
            if (options.method === 'POST' && !url.startsWith('http')) {
                if (!options.headers) {
                    options.headers = {};
                }
                
                // Add CSRF token if not already present
                if (!options.headers['X-CSRFToken']) {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
            }
            
            return originalFetch(url, options);
        };
    }
    
    // Add dismissible functionality to alerts
    document.querySelectorAll('.alert .btn-close').forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.classList.add('d-none');
        });
    });
});
