# gmail_backend.py
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import logging
import os
import json

logger = logging.getLogger(__name__)
def get_minio_url(object_key, for_backend=True):
    if for_backend:
        #host = "minio:9000"  # Docker service name for internal use
        host = "192.168.1.222:9000"
    else:
        #host = "localhost:9000"  # For browser access
        host = "192.168.1.222:9000"
    bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "stylescope-bucket")
    return f"http://{host}/{bucket}/{object_key}"




# api/gmail_helper.py
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# PASTE YOUR CREDENTIALS HERE
CLIENT_ID = settings.GMAIL_API_CLIENT_ID
CLIENT_SECRET = settings.GMAIL_API_CLIENT_SECRET
REDIRECT_URI = "http://localhost:8082/api/v1/admin/gmail/callback/"

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_FILE = '/app/secrets/gmail-token.json'

def get_oauth_url(request):
    """Get URL to start OAuth"""
    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    request.session['gmail_oauth_state'] = state
    return authorization_url

def handle_oauth_callback(request):
    """Handle OAuth callback and save token"""
    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }
    
    state = request.session.get('gmail_oauth_state')
    flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI)
    
    authorization_response = request.build_absolute_uri()
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    
    # Save token
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())
    
    return True

def get_gmail_service():
    """Get authenticated Gmail service"""
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token:
            token_data = json.load(token)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception("Not authenticated. Please authenticate first.")
    
    return build('gmail', 'v1', credentials=creds)

def send_email(to_email, subject, body, is_html=False):
    """Send an email"""
    try:
        service = get_gmail_service()
        
        message = MIMEMultipart() if is_html else MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        if is_html:
            message.attach(MIMEText(body, 'html'))
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False