# AI Mail Analyzer

An intelligent email analysis tool that uses AI to help you understand, categorize, and extract key information from your emails.

## Features

- Connect to any IMAP email server (Gmail, Outlook, etc.)
- Browse and view emails from different folders
- AI-powered email analysis:
  - Email summarization
  - Sentiment analysis
  - Action item extraction
  - Key points identification
  - Email categorization
  - Priority determination
  - Comprehensive analysis

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ai-mail-analyzer.git
   cd ai-mail-analyzer
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your OpenAI API key and other settings.

## Usage

1. Start the application:
   ```
   python app.py
   ```

2. Open your browser and go to `http://localhost:5000`

3. Log in with your email credentials

4. Browse your emails and use the AI analysis features

## Email Server Configuration

### Gmail
- Server: `imap.gmail.com`
- Port: `993`
- You need to enable "Less secure app access" or create an app password

### Outlook/Hotmail
- Server: `outlook.office365.com`
- Port: `993`

### Yahoo Mail
- Server: `imap.mail.yahoo.com`
- Port: `993`

## Security Notes

- Your email credentials are only stored in your session and are not saved permanently
- All communication with email servers is encrypted using SSL
- It's recommended to use app-specific passwords when available

## License

MIT
