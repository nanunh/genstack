# mailanalyser - Instructions

**Project ID:** 4cc01bae-804a-44e4-a240-579cfe09e23e
**Created:** 2025-10-28T18:42:35.996196

## Setup and Run Instructions

# AI Mail Analyzer - Setup Instructions

## Prerequisites
- Python 3.7 or higher
- An OpenAI API key
- Email account with IMAP access

## Setup Steps

1. **Clone or download the project files**

2. **Create a virtual environment**:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file
   - Set a secure Flask secret key

5. **Run the application**:
   ```
   python app.py
   ```

6. **Access the application**:
   - Open your browser and go to `http://localhost:5000`
   - Log in with your email credentials

## Email Configuration Notes

- For Gmail users:
  - You may need to enable "Less secure app access" or create an app password
  - Use `imap.gmail.com` as the server and `993` as the port

- For Outlook/Hotmail users:
  - Use `outlook.office365.com` as the server and `993` as the port

- For Yahoo Mail users:
  - Use `imap.mail.yahoo.com` as the server and `993` as the port

The application will connect to your email account, fetch your emails, and allow you to analyze them using AI-powered tools.