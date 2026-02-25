document.addEventListener('DOMContentLoaded', function() {
    // Current date tracking
    let currentDate = new Date();
    let currentYear = currentDate.getFullYear();
    let currentMonth = currentDate.getMonth() + 1; // JavaScript months are 0-indexed
    let selectedDay = null;
    
    // DOM elements
    const calendarGrid = document.getElementById('calendar-grid');
    const currentMonthYear = document.getElementById('current-month-year');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const selectedDateEl = document.getElementById('selected-date');
    const rahuTimeEl = document.getElementById('rahu-time');
    const yamakandamTimeEl = document.getElementById('yamakandam-time');
    
    // Month names for display
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    // Initialize calendar
    loadCalendar(currentYear, currentMonth);
    
    // Event listeners for navigation
    prevMonthBtn.addEventListener('click', function() {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }
        loadCalendar(currentYear, currentMonth);
    });
    
    nextMonthBtn.addEventListener('click', function() {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
        }
        loadCalendar(currentYear, currentMonth);
    });
    
    // Function to load calendar data from API
    function loadCalendar(year, month) {
        fetch(`/api/calendar/${year}/${month}`)
            .then(response => response.json())
            .then(data => {
                renderCalendar(data);
                updateMonthYearDisplay(year, month);
            })
            .catch(error => {
                console.error('Error loading calendar data:', error);
                alert('Failed to load calendar data. Please try again.');
            });
    }
    
    // Function to render the calendar
    function renderCalendar(data) {
        // Clear existing calendar
        calendarGrid.innerHTML = '';
        
        const firstDayOfWeek = data.first_day_of_week; // 0 = Monday, 6 = Sunday
        const days = data.days;
        
        // Add empty cells for days before the first day of the month
        for (let i = 0; i < firstDayOfWeek; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.className = 'calendar-day empty';
            calendarGrid.appendChild(emptyDay);
        }
        
        // Add cells for each day of the month
        days.forEach(day => {
            const dayCell = document.createElement('div');
            dayCell.className = 'calendar-day';
            dayCell.dataset.day = day.day;
            
            const dayNumber = document.createElement('div');
            dayNumber.className = 'day-number';
            dayNumber.textContent = day.day;
            dayCell.appendChild(dayNumber);
            
            const rahuIndicator = document.createElement('div');
            rahuIndicator.className = 'timing-indicator rahu';
            rahuIndicator.textContent = 'Rahu';
            dayCell.appendChild(rahuIndicator);
            
            const yamakandamIndicator = document.createElement('div');
            yamakandamIndicator.className = 'timing-indicator yamakandam';
            yamakandamIndicator.textContent = 'Yamakandam';
            dayCell.appendChild(yamakandamIndicator);
            
            // Create hidden time elements that will be shown on click
            const rahuTime = document.createElement('div');
            rahuTime.className = 'time-display rahu-time hidden';
            rahuTime.textContent = `${day.rahu[0]} - ${day.rahu[1]}`;
            dayCell.appendChild(rahuTime);
            
            const yamakandamTime = document.createElement('div');
            yamakandamTime.className = 'time-display yamakandam-time hidden';
            yamakandamTime.textContent = `${day.yamakandam[0]} - ${day.yamakandam[1]}`;
            dayCell.appendChild(yamakandamTime);
            
            // Store timing data as attributes
            dayCell.dataset.rahuStart = day.rahu[0];
            dayCell.dataset.rahuEnd = day.rahu[1];
            dayCell.dataset.yamakandamStart = day.yamakandam[0];
            dayCell.dataset.yamakandamEnd = day.yamakandam[1];
            
            // Add click event to show detailed timings
            dayCell.addEventListener('click', function() {
                // Remove selected class from previously selected day
                if (selectedDay) {
                    selectedDay.classList.remove('selected');
                    // Hide time displays in previously selected day
                    selectedDay.querySelector('.rahu-time').classList.add('hidden');
                    selectedDay.querySelector('.yamakandam-time').classList.add('hidden');
                }
                
                // Add selected class to clicked day
                this.classList.add('selected');
                selectedDay = this;
                
                // Show time displays in the clicked day cell
                this.querySelector('.rahu-time').classList.remove('hidden');
                this.querySelector('.yamakandam-time').classList.remove('hidden');
                
                // Highlight the indicators
                this.querySelector('.timing-indicator.rahu').classList.add('highlighted');
                this.querySelector('.timing-indicator.yamakandam').classList.add('highlighted');
                
                // Update the date display (but not the times since they're now in the cell)
                const dayNum = this.dataset.day;
                const monthName = monthNames[currentMonth - 1];
                selectedDateEl.textContent = `${dayNum} ${monthName} ${currentYear}`;
                
                // Clear the time elements below the calendar
                rahuTimeEl.textContent = '';
                yamakandamTimeEl.textContent = '';
            });
            
            calendarGrid.appendChild(dayCell);
        });
    }
    
    // Function to update the month and year display
    function updateMonthYearDisplay(year, month) {
        currentMonthYear.textContent = `${monthNames[month - 1]} ${year}`;
    }
});