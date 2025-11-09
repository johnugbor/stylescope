# Custom Gmail API Email Backend for Stylescope

from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import logging

logger = logging.getLogger(__name__)

class GmailAPIBackend(BaseEmailBackend):
    """
    Custom Gmail API backend for sending emails through Gmail API
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.service = None
    
    def open(self):
        """Initialize Gmail API service"""
        try:
            # Get credentials from settings
            client_id = getattr(settings, 'GMAIL_API_CLIENT_ID', None)
            client_secret = getattr(settings, 'GMAIL_API_CLIENT_SECRET', None)
            refresh_token = getattr(settings, 'GMAIL_API_REFRESH_TOKEN', None)
            
            if not all([client_id, client_secret, refresh_token]):
                raise ValueError("Gmail API credentials not configured properly")
            
            # Create credentials object
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )
            
            # Refresh token if needed
            if creds.expired:
                creds.refresh(Request())
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail API: {e}")
            if not self.fail_silently:
                raise
            return False
    
    def close(self):
        """Close the connection"""
        self.service = None
    
    def send_messages(self, email_messages):
        """Send multiple email messages"""
        if not self.service and not self.open():
            return 0
        
        sent_count = 0
        for message in email_messages:
            if self._send_message(message):
                sent_count += 1
        
        return sent_count
    
    def _send_message(self, email_message):
        """Send a single email message"""
        try:
            # Create MIME message
            if email_message.alternatives:
                # Multipart message with HTML
                msg = MIMEMultipart('alternative')
                
                # Add plain text part
                text_part = MIMEText(email_message.body, 'plain', 'utf-8')
                msg.attach(text_part)
                
                # Add HTML part
                for content, mimetype in email_message.alternatives:
                    if mimetype == 'text/html':
                        html_part = MIMEText(content, 'html', 'utf-8')
                        msg.attach(html_part)
            else:
                # Plain text message
                msg = MIMEText(email_message.body, 'plain', 'utf-8')
            
            # Set headers
            msg['To'] = ', '.join(email_message.to)
            msg['From'] = email_message.from_email
            msg['Subject'] = email_message.subject
            
            if email_message.cc:
                msg['Cc'] = ', '.join(email_message.cc)
            
            if email_message.bcc:
                msg['Bcc'] = ', '.join(email_message.bcc)
            
            # Convert to raw message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            
            # Send via Gmail API
            message_body = {'raw': raw_message}
            self.service.users().messages().send(
                userId='me', 
                body=message_body
            ).execute()
            
            logger.info(f"Email sent successfully to {', '.join(email_message.to)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            if not self.fail_silently:
                raise
            return False