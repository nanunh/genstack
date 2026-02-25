# Employee Assignment Tracker

## Overview
This is a web-based application for tracking employee work assignments for both hardware and software tasks. The application allows managers to create, edit, and track assignments for their team members.

## Features
- Create new assignments with employee name, type (hardware/software), description, due date, priority, and status
- View all assignments in a card-based layout
- Filter assignments by type (hardware/software), employee name, and status
- Edit existing assignments
- Update assignment status quickly
- Delete assignments
- Responsive design that works on desktop and mobile devices
- Data persistence using browser localStorage

## Technologies Used
- HTML5
- CSS3
- JavaScript (Vanilla JS)

## How to Use

### Installation
1. Clone or download this repository
2. Open the `index.html` file in any modern web browser

### Adding a New Assignment
1. Fill out the "Add New Assignment" form on the left side
2. Enter the employee name, select assignment type, provide a name and description
3. Set a due date, priority level, and current status
4. Click "Add Assignment" to create the new task

### Filtering Assignments
- Use the tab buttons (All, Hardware, Software) to quickly filter by type
- Use the filter form to search by employee name, type, or status
- Click "Apply Filters" to see filtered results
- Click "Clear Filters" to reset

### Editing Assignments
1. Click the "Edit" button on any assignment card
2. Update the information in the modal form
3. Click "Update Assignment" to save changes

### Updating Status
1. Click the "Update Status" button on any assignment card
2. Select the new status from the dropdown
3. Click "Update Status" to save

### Deleting Assignments
1. Click the "Delete" button on any assignment card
2. Confirm the deletion when prompted

## Data Storage
All assignment data is stored in your browser's localStorage. This means:
- Data persists between sessions
- Data is stored only on your local device
- Clearing browser data will erase all assignments

## Browser Compatibility
This application works on all modern browsers including:
- Chrome
- Firefox
- Safari
- Edge

## License
This project is open source and available for personal and commercial use.
