import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an HTML email. Returns True on success, False on failure."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = to

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_DEFAULT_SENDER, to, msg.as_string())

        return True

    except Exception as e:
        print(f"[Email] Failed to send to {to}: {e}")
        return False


def send_password_reset_email(to: str, reset_url: str) -> bool:
    """Send a password reset email with the reset link."""
    subject = "Reset Your FullStack Password"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 40px 0;">
        <div style="max-width: 500px; margin: 0 auto; background: #fff;
                    border-radius: 10px; overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 30px; text-align: center;">
                <h1 style="color: #fff; margin: 0; font-size: 24px;">🚀 FullStack</h1>
            </div>
            <div style="padding: 36px 32px;">
                <h2 style="color: #1a1a2e; margin-top: 0;">Reset Your Password</h2>
                <p style="color: #555; line-height: 1.6;">
                    We received a request to reset the password for your account.
                    Click the button below to choose a new password.
                    This link will expire in <strong>1 hour</strong>.
                </p>
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{reset_url}"
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: #fff; text-decoration: none; padding: 14px 32px;
                              border-radius: 8px; font-size: 16px; font-weight: 600;
                              display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #888; font-size: 13px;">
                    If you didn't request a password reset, you can safely ignore this email.
                    Your password will not be changed.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
                <p style="color: #aaa; font-size: 12px; margin: 0;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{reset_url}" style="color: #667eea; word-break: break-all;">
                        {reset_url}
                    </a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(to, subject, html_body)
