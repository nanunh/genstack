# babysitter-booking-app - Instructions

**Project ID:** e1a04999-5639-4c87-9d16-d7771895c215
**Created:** 2025-10-15T08:07:29.811532

## Setup and Run Instructions

To set up and run the BabySitter Booking application:

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to http://localhost:5000

6. You can register as either a parent or a sitter:
   - Parents can browse sitters, book appointments, and leave reviews
   - Sitters can create profiles, set rates, and accept/decline bookings

The application uses SQLite for the database, which will be created automatically when you first run the app.