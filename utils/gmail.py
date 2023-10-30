from __future__ import print_function
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import base64
import re

SCOPES = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.settings.basic',
            'https://www.googleapis.com/auth/gmail.settings.sharing'
]

def initialize_app():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            print('No labels found.')
            return
        print('Labels:')
        for label in labels:
            print(label['name'])

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


class GmailConnector:
    def __init__(self, credentials_file='credentials.json', token_file='token.json', scopes=None):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = SCOPES
        self.credentials = None
        self.service = None

    def connect(self):
        """Connects to the Gmail API and lists the user's Gmail labels."""
        if os.path.exists(self.token_file):
            self.credentials = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes)
                self.credentials = flow.run_local_server(port=0)
            with open(self.token_file, 'w') as token:
                token.write(self.credentials.to_json())

        try:
            self.service = build('gmail', 'v1', credentials=self.credentials)
            return self.service
        except Exception as e:
            print(f'Failed to connect to Gmail: {e}')
    
    def get_email_info(self):
        """
        Prints out the email address of the account it connects to.
        Args:
        """
        if not self.service:
            print('Not connected to Gmail.')
            return 

        try:
            profile = self.service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'No email address found')
            print(f'Connected to Gmail account: {email_address}')
            return email_address
        except Exception as e:
            print(f'Failed to retrieve email information: {e}')
            return 

    def read_emails_in_timeframe(self, start_date, end_date):
        """Reads emails within a specified timeframe.

        Args:
        start_date (str): Start date in the format 'YYYY/MM/DD'.
        end_date (str): End date in the format 'YYYY/MM/DD'.

        Returns:
        List[Tuple[str, str, str]]: A list of tuples, each containing a message ID, subject, and sender.
        """
        if not self.service:
            print('Not connected to Gmail.')
            return []

        query = f'after:{start_date} before:{end_date}'
        message_list = []
        try:
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            
            for message in messages:
                msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
                subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), 'No Subject')
                sender = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), 'Unknown Sender')
                message_list.append((msg['id'], subject, sender))

        except Exception as e:
            print(f'Failed to retrieve emails: {e}')

        return message_list
    
    def view_email_contents(self, message_id):
        """Views the sender, time, recipients, and contents of an email.

        Args:
        message_id (str): The ID of the message to view.

        Returns:
        dict: A dictionary containing the time, sender, recipients, and content of the email.
        """
        if not self.service:
            print('Not connected to Gmail.')
            return []

        try:
            msg = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
            headers = msg['payload']['headers']
            sender = next(header['value'] for header in headers if header['name'] == 'From')
            date = next(header['value'] for header in headers if header['name'] == 'Date')
            to = next(header['value'] for header in headers if header['name'] == 'To')
            recipients = to.split(', ')
            parts = msg['payload'].get('parts', [])
            email_content = ''
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data', '')
                    email_content += base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
            
            # Remove unwanted characters and sequences of characters
            email_content = email_content.replace('\xa0', ' ').replace('\u200c', '')
            email_content = re.sub(r'\r\n', '\n', email_content)
            email_content = re.sub(r'https?://[^\s]+', '[URL]', email_content)  # Replace URLs with [URL]

            email_chain = []
            email_texts = re.split(r'On .+ wrote:', email_content)
            for email_text in email_texts:
                email_chain.append({
                    'time': date,
                    'sender': sender,
                    'recipients': recipients,
                    'content': email_text.strip()
                })
            return email_chain
        except Exception as e:
            print(f'Failed to retrieve email contents: {e}')
            return []

    def send_email(self, subject, body, recipients):
        """Send an email message.

        Args:
            subject (str): The subject of the email message.
            body (str): The body text of the email message.
            recipients (list): A list of recipient email addresses.

        Returns:
            Sent Message.
        """
        if not self.service:
            print('Gmail service not connected.')
            return None

        # Join the list of email addresses into a single string, separated by commas
        recipients_str = ', '.join(recipients)

        message = MIMEMultipart()
        message['to'] = recipients_str  # Corrected this line
        message['subject'] = subject
        msg = MIMEText(body)
        message.attach(msg)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        try:
            message = (
                self.service.users()
                .messages()
                .send(userId='me', body={'raw': raw_message})
                .execute()
            )
            print(f'Message sent to {recipients_str}. Message Id: {message.get("id")}')
            return message
        except Exception as error:
            print(f'An error occurred: {error}')
            return None


initialize_app()

# Usage:
GMAIL = GmailConnector()
GMAIL.connect()

# emails = GMAIL.read_emails_in_timeframe('2023/10/20', '2023/10/27')
# GMAIL.send_email('Test Subject', 'Test Body', 'joeisenman@davidson.edu')
# email_contents = GMAIL.view_email_contents('18b6719ce5640570')
# email_contents