document.addEventListener('DOMContentLoaded', function() {
    const nameInput = document.getElementById('name');
    const greetBtn = document.getElementById('greet-btn');
    const greetingElement = document.getElementById('greeting');
    
    // Apply initial colorful styling
    applyColorfulStyling();

    // Function to update greeting
    function updateGreeting(name) {
        fetch('/greet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name })
        })
        .then(response => response.json())
        .then(data => {
            greetingElement.textContent = data.message;
            
            // Enhanced animation with colors
            greetingElement.classList.add('animated');
            
            // Change background color randomly for a colorful effect
            const randomColor = getRandomColor();
            greetingElement.style.backgroundColor = randomColor;
            greetingElement.style.color = getContrastColor(randomColor);
            
            setTimeout(() => {
                greetingElement.classList.remove('animated');
                // Fade back to original colors
                greetingElement.style.transition = 'background-color 1s, color 1s';
                greetingElement.style.backgroundColor = '';
                greetingElement.style.color = '';
            }, 1500);
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }

    // Event listener for button click
    greetBtn.addEventListener('click', function() {
        animateButton(this);
        const name = nameInput.value.trim();
        if (name) {
            updateGreeting(name);
        } else {
            updateGreeting('World');
        }
    });

    // Event listener for Enter key
    nameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const name = nameInput.value.trim();
            if (name) {
                updateGreeting(name);
            } else {
                updateGreeting('World');
            }
        }
    });
    
    // Event listener for input focus
    nameInput.addEventListener('focus', function() {
        this.style.boxShadow = `0 0 8px ${getRandomColor()}`;
    });
    
    nameInput.addEventListener('blur', function() {
        this.style.boxShadow = '';
    });
    
    // Helper function to generate random colors
    function getRandomColor() {
        const letters = '0123456789ABCDEF';
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
    
    // Helper function to determine contrast color (black or white) based on background
    function getContrastColor(hexColor) {
        // Convert hex to RGB
        const r = parseInt(hexColor.substr(1, 2), 16);
        const g = parseInt(hexColor.substr(3, 2), 16);
        const b = parseInt(hexColor.substr(5, 2), 16);
        
        // Calculate luminance - brighter colors need dark text
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.5 ? '#000000' : '#FFFFFF';
    }
    
    // Function to animate button on click
    function animateButton(button) {
        button.classList.add('button-pressed');
        setTimeout(() => {
            button.classList.remove('button-pressed');
        }, 200);
    }
    
    // Apply colorful styling to elements
    function applyColorfulStyling() {
        // Add a subtle color transition to the input field
        nameInput.style.transition = 'all 0.3s ease';
        
        // Make the button more colorful
        greetBtn.style.background = 'linear-gradient(45deg, #ff7b00, #ff006a)';
        greetBtn.style.color = 'white';
        greetBtn.style.border = 'none';
        greetBtn.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
        greetBtn.style.transition = 'all 0.3s ease';
        
        // Hover effect for button
        greetBtn.addEventListener('mouseover', function() {
            this.style.background = 'linear-gradient(45deg, #ff006a, #ff7b00)';
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 6px 8px rgba(0, 0, 0, 0.15)';
        });
        
        greetBtn.addEventListener('mouseout', function() {
            this.style.background = 'linear-gradient(45deg, #ff7b00, #ff006a)';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
        });
    }
});