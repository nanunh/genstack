import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime

class EmailService:
    def __init__(self):
        self.connection = None
        self.username = None
    
    def connect(self, username, password, server, port=993):
        """Connect to the email server"""
        try:
            self.connection = imaplib.IMAP4_SSL(server, port)
            self.connection.login(username, password)
            self.username = username
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to email server: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the email server"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass  # Ignore errors during logout
            self.connection = None
    
    def list_folders(self):
        """List all available folders/mailboxes"""
        if not self.connection:
            raise Exception("Not connected to email server")
        
        result, folders = self.connection.list()
        folder_list = []
        
        if result == 'OK':
            for folder in folders:
                folder_parts = folder.decode().split(' "/" ')
                if len(folder_parts) > 1:
                    folder_name = folder_parts[1].strip('"')
                    folder_list.append(folder_name)
        
        return folder_list
    
    def fetch_emails(self, folder='INBOX', limit=10):
        """Fetch emails from the specified folder"""
        if not self.connection:
            raise Exception("Not connected to email server")
        
        # Select the mailbox/folder
        result, data = self.connection.select(folder)
        if result != 'OK':
            raise Exception(f"Failed to select folder: {folder}")
        
        # Search for all emails in the folder
        result, data = self.connection.search(None, 'ALL')
        if result != 'OK':
            raise Exception("Failed to search for emails")
        
        # Get email IDs
        email_ids = data[0].split()
        
        # Limit the number of emails to fetch (most recent first)
        if limit > 0 and len(email_ids) > limit:
            email_ids = email_ids[-limit:]
        
        emails = []
        
        for email_id in reversed(email_ids):  # Process newest first
            result, data = self.connection.fetch(email_id, '(RFC822)')
            if result != 'OK':
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract email details
            subject = self._decode_email_header(msg['Subject'])
            from_addr = self._decode_email_header(msg['From'])
            date_str = msg['Date']
            
            # Parse date
            try:
                date_obj = email.utils.parsedate_to_datetime(date_str)
                date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            except:
                date = date_str
            
            # Get email body preview
            body = self._get_email_body(msg)
            body_preview = body[:150] + '...' if len(body) > 150 else body
            
            emails.append({
                'id': email_id.decode(),
                'subject': subject,
                'from': from_addr,
                'date': date,
                'preview': body_preview,
                'has_attachments': self._has_attachments(msg)
            })
        
        return emails
    
    def get_email_content(self, email_id):
        """Get the full content of a specific email"""
        if not self.connection:
            raise Exception("Not connected to email server")
        
        result, data = self.connection.fetch(email_id.encode(), '(RFC822)')
        if result != 'OK':
            raise Exception(f"Failed to fetch email with ID: {email_id}")
        
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Extract email details
        subject = self._decode_email_header(msg['Subject'])
        from_addr = self._decode_email_header(msg['From'])
        to_addr = self._decode_email_header(msg['To'])
        date_str = msg['Date']
        
        # Parse date
        try:
            date_obj = email.utils.parsedate_to_datetime(date_str)
            date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
        except:
            date = date_str
        
        # Get email body
        body = self._get_email_body(msg)
        
        # Get attachments info
        attachments = []
        if self._has_attachments(msg):
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename:
                    filename = self._decode_email_header(filename)
                    attachments.append({
                        'filename': filename,
                        'size': len(part.get_payload(decode=True))
                    })
        
        return {
            'id': email_id,
            'subject': subject,
            'from': from_addr,
            'to': to_addr,
            'date': date,
            'body': body,
            'attachments': attachments
        }
    
    def _decode_email_header(self, header):
        """Decode email header"""
        if header is None:
            return ''
        
        decoded_header = decode_header(header)
        header_parts = []
        
        for part, encoding in decoded_header:
            if isinstance(part, bytes):
                if encoding:
                    try:
                        part = part.decode(encoding)
                    except:
                        part = part.decode('utf-8', errors='replace')
                else:
                    part = part.decode('utf-8', errors='replace')
            header_parts.append(str(part))
        
        return ' '.join(header_parts)
    
    def _get_email_body(self, msg):
        """Extract the email body"""
        if msg.is_multipart():
            body = ''
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break  # Prefer plain text
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    try:
                        html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        # Simple HTML to text conversion
                        body = re.sub('<[^<]+?>', '', html)
                    except:
                        pass
            
            return body
        else:
            # Not multipart - get the content directly
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                if msg.get_content_type() == 'text/html':
                    # Simple HTML to text conversion
                    body = re.sub('<[^<]+?>', '', body)
                return body
            except:
                return ''
    
    def _has_attachments(self, msg):
        """Check if the email has attachments"""
        if not msg.is_multipart():
            return False
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            if 'attachment' in str(part.get('Content-Disposition')):
                return True
        
        return False
