import json
import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from fake_useragent import UserAgent
import boto3
from models import Task, SpotifyFamilyAccount
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from urllib.parse import urlparse
from src.utils.challenge_solver import solve_captcha
from src.utils.helper import login, saveScreenshotThrowException
from tempfile import mkdtemp
import requests

load_dotenv()

def change_email_api(event, context):
    options = webdriver.ChromeOptions()
    ua = UserAgent()
    userAgent = ua.random

    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument(f'user-agent={userAgent}')

    driver = webdriver.Chrome('/opt/chromedriver', options=options)
    driver.set_window_size(1280, 1696)
    driver.set_script_timeout(60)  # Set script timeout to 60 seconds
    s3 = boto3.client('s3')

    public_ip = None
    try:
        ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
        public_ip = ip_response.json()['ip']
        print(f"Current public IP: {public_ip}")
    except Exception as e:
        print(f"Failed to retrieve public IP: {str(e)}")

    import random

    stealth_args = {
        'languages': ["en-US", "en"],
        'vendor': "Google Inc.",
        'platform': "Win32",
        'webgl_vendor': "Intel Inc.",
        'renderer': "Intel Iris OpenGL Engine",
        'fix_hairline': True,
    }

    if random.random() < 0.5:
        stealth_args['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'
        print("Using custom user agent")

    stealth(driver, **stealth_args)

    # Create database engine and session
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        if 'task_id' not in event:
            print("Warning: 'task_id' not found in event object")
            event['task_id'] = 'default_task_id'

        # Update task with IP address
        task = session.query(Task).filter_by(id=event['task_id']).first()
        if task and public_ip:
            task.used_ip_address = public_ip
            session.commit()

        login(driver, event, s3)

        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Challenge found", driver.current_url)
            solve_captcha(driver, event)
            time.sleep(2)

        print("Challenge solved", driver.current_url)

        # Navigate to the profile page
        print("Navigating to account overview page...")
        driver.get('https://www.spotify.com/in-en/account/profile/')
        
        # Function to get reCAPTCHA token
        get_recaptcha_token_script = """
        function waitForRecaptchaToken() {
            return new Promise((resolve) => {
                const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name.includes('https://www.google.com/recaptcha/enterprise/reload')) {
                            observer.disconnect();
                            fetch(entry.name)
                                .then(response => response.text())
                                .then(text => {
                                    const match = text.match(/"rresp","(.*?)"/);
                                    if (match) {
                                        resolve(match[1]);
                                    } else {
                                        resolve(null);
                                    }
                                });
                        }
                    }
                });
                observer.observe({entryTypes: ['resource']});
            });
        }
        return await waitForRecaptchaToken();
        """

        print("Waiting for reCAPTCHA token...")
        recaptcha_token = driver.execute_async_script(get_recaptcha_token_script)
        if recaptcha_token:
            print("reCAPTCHA token obtained successfully")
            print("Google reCAPTCHA POST request response:")
            print(json.dumps(recaptcha_token, indent=2))
        else:
            print("Failed to obtain reCAPTCHA token")

        print("Waiting for page to load...")
        time.sleep(5)  # Give the page some time to load

        print("Getting profile data...")
        # Get profile data
        script = """
        async function getProfileData() {
            const response = await fetch('https://www.spotify.com/api/account-settings/v1/profile');
            return await response.json();
        }
        return getProfileData();
        """
        profile_data = driver.execute_script(script)
        print("Profile data obtained:", json.dumps(profile_data, indent=2))

        # Prepare payload for email change
        payload = {
            "password": event['password'],
            "profile": {
                "email": event['new_email'],
                "gender": profile_data['profile']['gender'],
                "birthdate": profile_data['profile']['birthdate'],
                "country": profile_data['profile']['country']
            }
        }
        if recaptcha_token:
            payload['recaptcha_token'] = recaptcha_token

        print("Payload prepared:", json.dumps(payload, indent=2))

        # Change email
        change_email_script = f"""
        async function changeEmail() {{
            const payload = {json.dumps(payload)};
            const response = await fetch('https://www.spotify.com/api/account-settings/v1/profile', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify(payload)
            }});
            return {{
                status: response.status,
                data: await response.json()
            }};
        }}
        return changeEmail();
        """
        print("Executing email change script...")
        response = driver.execute_script(change_email_script)
        print("Email change response:", json.dumps(response, indent=2))

        if response['status'] == 200:
            print("Email changed successfully")
            
            # Update database
            family_account = session.query(SpotifyFamilyAccount).filter_by(email=event['email']).first()
            if family_account:
                family_account.past_emails.append(family_account.email)
                family_account.email = event['new_email']
                session.commit()
                print(f"Database updated: Email changed from {event['email']} to {event['new_email']}")

            # Update task status
            task = session.query(Task).filter_by(id=event['task_id']).first()
            if task:
                task.status = 'COMPLETED'
                task.updated_at = datetime.now(timezone.utc)
                session.commit()
                print(f"Task {event['task_id']} status updated to COMPLETED")

            return {
                'statusCode': 200,
                'body': json.dumps('Email updated successfully')
            }
        else:
            print(f"Failed to change email. Status code: {response['status']}")
            print(f"Response: {response['data']}")
            
            saveScreenshotThrowException(driver, s3, "Failed to change email. Screenshot saved as ")

            # Update task status to FAILED
            task = session.query(Task).filter_by(id=event['task_id']).first()
            if task:
                task.status = 'FAILED'
                task.error = f"Failed to change email. Status code: {response['status']}"
                task.updated_at = datetime.now(timezone.utc)
                session.commit()
                print(f"Task {event['task_id']} status updated to FAILED")

            return {
                'statusCode': 500,
                'body': json.dumps('Failed to update email')
            }

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
        saveScreenshotThrowException(driver, s3, "An error occurred. Screenshot saved as ")

        # Update task status to FAILED
        task = session.query(Task).filter_by(id=event['task_id']).first()
        if task:
            task.status = 'FAILED'
            task.error = str(e)
            task.updated_at = datetime.now(timezone.utc)
            session.commit()
            print(f"Task {event['task_id']} status updated to FAILED due to error")

        return {
            'statusCode': 500,
            'body': json.dumps(f'An error occurred: {str(e)}')
        }

    finally:
        driver.get('https://www.spotify.com/in-en/logout/')
        print("Logging out")
        time.sleep(0.5)
        driver.quit()
        session.close()

