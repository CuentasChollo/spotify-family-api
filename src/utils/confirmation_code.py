import imaplib
import email
import re
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from datetime import timezone

def get_confirmation_code(target_email):
    # Load environment variables
    load_dotenv()
    
    # Gmail account credentials
    gmail_user = os.getenv('GMAIL_EMAIL')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD')

    # Connect to Gmail
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(gmail_user, gmail_password)
    mail.select('inbox')

    # Search for emails from Spotify to the target email
    search_criteria = f'(FROM "no-reply@alerts.spotify.com" TO "{target_email}")'
    _, message_numbers = mail.search(None, search_criteria)

    # Set the time constraint (2 minutes ago)
    time_constraint = datetime.now(timezone.utc) - timedelta(minutes=2)

    for num in message_numbers[0].split()[::-1]:  # Reverse order to get the latest email first
        _, msg_data = mail.fetch(num, '(RFC822)')
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)

        # Check the email's date
        email_date = parsedate_to_datetime(email_message['Date'])
        if email_date < time_constraint:
            # If the email is older than 2 minutes, stop processing
            break

        subject = email_message['subject']
        if subject:
            # Extract the confirmation code from the subject
            match = re.search(r'\b(\d{6})\b', subject)
            if match:
                confirmation_code = match.group(1)
                mail.close()
                mail.logout()
                return confirmation_code

    mail.close()
    mail.logout()
    return None

