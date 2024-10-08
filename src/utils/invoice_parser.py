import imaplib
import email
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import os
import re

def get_invoice_date(target_email):
    # Load environment variables
    load_dotenv()
    
    print("Starting invoice date finder")
    # Gmail account credentials
    gmail_user = os.getenv('GMAIL_EMAIL')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD')

    # Connect to Gmail
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(gmail_user, gmail_password)
    mail.select('inbox')

    # Search for emails from CheaperShopGlobal with "completed" anywhere in the subject and target_email in the body
    search_criteria = f'(SUBJECT "*completed*" BODY "{target_email}")'
    _, message_numbers = mail.search(None, search_criteria)

    # Print the number of emails that met the conditions
    print(f"Number of emails found: {len(message_numbers[0].split())}")

    if message_numbers[0]:
        latest_email_id = message_numbers[0].split()[-1]
        _, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        print("Email message found")
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        content = part.get_payload(decode=True).decode()
                    except:
                        print(f"Error decoding {content_type} content")
                        continue

                    if content_type == "text/html":
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text()

                    print(f"Processing {content_type} content")
                    
                    # Find the duration
                    duration_match = re.search(r'Duration:\s*(\d+)\s*Months', content, re.IGNORECASE)
                    print(f"Debug: duration_match = {duration_match}")  # Added debug print
                    if duration_match:
                        months = int(duration_match.group(1))
                        
                        # Find the first occurrence of a date in the format dd/mm/yyyy
                        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', content)
                        if date_match:
                            order_date_str = date_match.group(1)
                            order_date = datetime.strptime(order_date_str, "%d/%m/%Y")
                            
                            # Calculate the premium end date
                            premium_end_date = order_date + relativedelta(months=months)
                            return premium_end_date.isoformat()
                    
                    print(f"Could not find required information in {content_type} content")

    mail.close()
    mail.logout()
    return None

def main():
    target_email = "familly009@sampledomain.com"  # Replace with the actual email you're searching for
    result = get_invoice_date(target_email)
    if result:
        print(f"Premium end date: {result}")
    else:
        print("Could not find premium end date")

if __name__ == "__main__":
    main()