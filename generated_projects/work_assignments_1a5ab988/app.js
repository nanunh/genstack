// DOM Elements
const assignmentForm = document.getElementById('assignment-form');
const assignmentList = document.getElementById('assignment-list');
const tabButtons = document.querySelectorAll('.tab-btn');
const editModal = document.getElementById('edit-modal');
const statusModal = document.getElementById('status-modal');
const editForm = document.getElementById('edit-form');
const statusForm = document.getElementById('status-form');
const closeModalButtons = document.querySelectorAll('.close-modal');
const applyFiltersBtn = document.getElementById('apply-filters');
const clearFiltersBtn = document.getElementById('clear-filters');
const noAssignmentsMsg = document.querySelector('.no-assignments');

// Assignment data storage
let assignments = JSON.parse(localStorage.getItem('assignments')) || [];
let currentFilter = 'all';
let activeFilters = {
    employee: '',
    type: '',
    status: ''
};

// Initialize the application
function init() {
    renderAssignments();
    setupEventListeners();
}

// Set up all event listeners
function setupEventListeners() {
    // Form submission for new assignments
    assignmentForm.addEventListener('submit', handleNewAssignment);
    
    // Tab filtering
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            currentFilter = button.dataset.type;
            renderAssignments();
        });
    });
    
    // Close modals
    closeModalButtons.forEach(button => {
        button.addEventListener('click', () => {
            editModal.style.display = 'none';
            statusModal.style.display = 'none';
        });
    });
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === editModal) editModal.style.display = 'none';
        if (e.target === statusModal) statusModal.style.display = 'none';
    });
    
    // Edit form submission
    editForm.addEventListener('submit', handleEditAssignment);
    
    // Status form submission
    statusForm.addEventListener('submit', handleStatusUpdate);
    
    // Filter controls
    applyFiltersBtn.addEventListener('click', applyFilters);
    clearFiltersBtn.addEventListener('click', clearFilters);
}

// Handle new assignment submission
function handleNewAssignment(e) {
    e.preventDefault();
    
    const newAssignment = {
        id: Date.now().toString(),
        employee: document.getElementById('employee-name').value.trim(),
        type: document.getElementById('assignment-type').value,
        name: document.getElementById('assignment-name').value.trim(),
        description: document.getElementById('assignment-description').value.trim(),
        dueDate: document.getElementById('due-date').value,
        priority: document.getElementById('priority').value,
        status: document.getElementById('status').value,
        createdAt: new Date().toISOString()
    };
    
    assignments.push(newAssignment);
    saveAssignments();
    assignmentForm.reset();
    renderAssignments();
}

// Handle edit assignment submission
function handleEditAssignment(e) {
    e.preventDefault();
    
    const id = document.getElementById('edit-id').value;
    const index = assignments.findIndex(assignment => assignment.id === id);
    
    if (index !== -1) {
        assignments[index] = {
            ...assignments[index],
            employee: document.getElementById('edit-employee-name').value.trim(),
            type: document.getElementById('edit-assignment-type').value,
            name: document.getElementById('edit-assignment-name').value.trim(),
            description: document.getElementById('edit-assignment-description').value.trim(),
            dueDate: document.getElementById('edit-due-date').value,
            priority: document.getElementById('edit-priority').value,
            status: document.getElementById('edit-status').value,
            updatedAt: new Date().toISOString()
        };
        
        saveAssignments();
        renderAssignments();
        editModal.style.display = 'none';
    }
}

// Handle status update submission
function handleStatusUpdate(e) {
    e.preventDefault();
    
    const id = document.getElementById('status-id').value;
    const newStatus = document.getElementById('status-update').value;
    const index = assignments.findIndex(assignment => assignment.id === id);
    
    if (index !== -1) {
        assignments[index] = {
            ...assignments[index],
            status: newStatus,
            updatedAt: new Date().toISOString()
        };
        
        saveAssignments();
        renderAssignments();
        statusModal.style.display = 'none';
    }
}

// Open edit modal with assignment data
function openEditModal(id) {
    const assignment = assignments.find(a => a.id === id);
    
    if (assignment) {
        document.getElementById('edit-id').value = assignment.id;
        document.getElementById('edit-employee-name').value = assignment.employee;
        document.getElementById('edit-assignment-type').value = assignment.type;
        document.getElementById('edit-assignment-name').value = assignment.name;
        document.getElementById('edit-assignment-description').value = assignment.description || '';
        document.getElementById('edit-due-date').value = assignment.dueDate;
        document.getElementById('edit-priority').value = assignment.priority;
        document.getElementById('edit-status').value = assignment.status;
        
        editModal.style.display = 'block';
    }
}

// Open status update modal
function openStatusModal(id) {
    const assignment = assignments.find(a => a.id === id);
    
    if (assignment) {
        document.getElementById('status-id').value = assignment.id;
        document.getElementById('status-update').value = assignment.status;
        
        statusModal.style.display = 'block';
    }
}

// Delete an assignment
function deleteAssignment(id) {
    if (confirm('Are you sure you want to delete this assignment?')) {
        assignments = assignments.filter(assignment => assignment.id !== id);
        saveAssignments();
        renderAssignments();
    }
}

// Apply filters to assignments
function applyFilters() {
    activeFilters = {
        employee: document.getElementById('filter-employee').value.trim().toLowerCase(),
        type: document.getElementById('filter-type').value,
        status: document.getElementById('filter-status').value
    };
    
    renderAssignments();
}

// Clear all filters
function clearFilters() {
    document.getElementById('filter-employee').value = '';
    document.getElementById('filter-type').value = '';
    document.getElementById('filter-status').value = '';
    
    activeFilters = {
        employee: '',
        type: '',
        status: ''
    };
    
    renderAssignments();
}

// Filter assignments based on current filters
function filterAssignments() {
    let filtered = [...assignments];
    
    // Apply tab filter
    if (currentFilter !== 'all') {
        filtered = filtered.filter(assignment => assignment.type === currentFilter);
    }
    
    // Apply active filters
    if (activeFilters.employee) {
        filtered = filtered.filter(assignment => 
            assignment.employee.toLowerCase().includes(activeFilters.employee)
        );
    }
    
    if (activeFilters.type) {
        filtered = filtered.filter(assignment => assignment.type === activeFilters.type);
    }
    
    if (activeFilters.status) {
        filtered = filtered.filter(assignment => assignment.status === activeFilters.status);
    }
    
    return filtered;
}

// Render assignments to the DOM
function renderAssignments() {
    const filteredAssignments = filterAssignments();
    assignmentList.innerHTML = '';
    
    if (filteredAssignments.length === 0) {
        assignmentList.appendChild(noAssignmentsMsg.cloneNode(true));
        return;
    }
    
    // Sort assignments by due date (closest first)
    filteredAssignments.sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate));
    
    filteredAssignments.forEach(assignment => {
        const template = document.getElementById('assignment-template');
        const clone = document.importNode(template.content, true);
        
        // Set assignment data
        const item = clone.querySelector('.assignment-item');
        item.dataset.id = assignment.id;
        item.dataset.type = assignment.type;
        item.dataset.status = assignment.status;
        
        // Set title and metadata
        clone.querySelector('.assignment-title').textContent = assignment.name;
        
        const typeElement = clone.querySelector('.assignment-type');
        typeElement.textContent = assignment.type === 'hardware' ? 'Hardware' : 'Software';
        typeElement.dataset.type = assignment.type;
        
        const priorityElement = clone.querySelector('.assignment-priority');
        priorityElement.textContent = `${assignment.priority.charAt(0).toUpperCase() + assignment.priority.slice(1)} Priority`;
        priorityElement.dataset.priority = assignment.priority;
        
        // Set body content
        clone.querySelector('.assignment-employee span').textContent = assignment.employee;
        clone.querySelector('.assignment-description span').textContent = assignment.description || 'No description provided';
        
        // Format date
        const dueDate = new Date(assignment.dueDate);
        const formattedDate = dueDate.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        clone.querySelector('.assignment-due-date span').textContent = formattedDate;
        
        // Set status
        const statusSpan = clone.querySelector('.assignment-status span');
        let statusText = '';
        
        switch(assignment.status) {
            case 'not-started':
                statusText = 'Not Started';
                break;
            case 'in-progress':
                statusText = 'In Progress';
                break;
            case 'completed':
                statusText = 'Completed';
                break;
            default:
                statusText = assignment.status;
        }
        
        statusSpan.textContent = statusText;
        statusSpan.dataset.status = assignment.status;
        
        // Set up action buttons
        clone.querySelector('.btn-edit').addEventListener('click', () => openEditModal(assignment.id));
        clone.querySelector('.btn-delete').addEventListener('click', () => deleteAssignment(assignment.id));
        clone.querySelector('.btn-status').addEventListener('click', () => openStatusModal(assignment.id));
        
        // Add to DOM
        assignmentList.appendChild(clone);
    });
}

// Save assignments to localStorage
function saveAssignments() {
    localStorage.setItem('assignments', JSON.stringify(assignments));
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', init);
