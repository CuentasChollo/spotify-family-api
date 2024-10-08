import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
from tempfile import mkdtemp
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import boto3
from selenium_stealth import stealth
from fake_useragent import UserAgent
import re
import requests
import json
import uuid
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from src.utils.challenge_solver import solve_captcha
from src.utils.helper import login, saveScreenshotThrowException, send_keys_naturally
from dotenv import load_dotenv
import os
from src.utils.invoice_parser import get_invoice_date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task, FamilyUpdateTaskPayload, SpotifyFamilyAccount


load_dotenv()

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def retrieve_family_data(event, context):
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

    session = Session()
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
            solve_captcha(driver, event, session)  # Pass the session here
            time.sleep(2)

        
        print("Challenge solved", driver.current_url)
        saveScreenshotThrowException(driver, s3, "Challenge solved", throw=False)

        # Extract premium end date
        print("Navigating to account overview page...")
        driver.get('https://www.spotify.com/in-en/account/overview/')
        time.sleep(5)  # Give the page some time to load

        try:
            premium_end_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-testid='description'] b.recurring-date"))
            )
            premium_end_date_str = premium_end_element.text
            # Convert the date to ISO format
            premium_end_date = datetime.strptime(premium_end_date_str, "%d/%m/%y").isoformat()
            print(f"Premium end date: {premium_end_date}")
        except:
            print("Could not find premium end date on the website. Searching email for invoice.")
            premium_end_date = get_invoice_date(event['email'])
            if premium_end_date:
                print(f"Premium end date found in email: {premium_end_date}")
            else:
                premium_end_date = "Not found"
                print("Could not find premium end date in email")

        # Extract user ID and display name
        driver.get('https://www.spotify.com/in-en/account/profile/')
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='username-field'] p"))
        )
        username_element = driver.find_element(By.CSS_SELECTOR, "div[data-testid='username-field'] p")
        user_id = username_element.text
        print(f"Extracted user ID: {user_id}")

        # Request access token
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        token_url = 'https://accounts.spotify.com/api/token'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        token_response = requests.post(token_url, data=token_data)
        access_token = token_response.json()['access_token']

        # Get user display name
        user_url = f'https://api.spotify.com/v1/users/{user_id}'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        user_response = requests.get(user_url, headers=headers)
        user_data = user_response.json()
        display_name = user_data.get('display_name', 'Unknown')
        print(f"User display name: {display_name}")

        print("Navigating to family page...")
        driver.get('https://www.spotify.com/in-en/account/family/')
        time.sleep(5)  # Give the page some time to load

        driver.execute_script("window.scrollTo(0, 500)")
        print("Scrolling till the end")

        # Switch to the iframe
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "family-web-iframe")))
        print("Switched to iframe")

        # Wait for and extract address
        address_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h2[@data-encore-id='type']/following-sibling::div[1]"))
        )
        address = address_element.text
        print(f"Family address: {address}")

        # Extract number of people
        family_list = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[data-encore-id='typeList']"))
        )
        people_elements = family_list.find_elements(By.CSS_SELECTOR, "li > a")
        num_people = len(people_elements)
        print(f"Number of people in family plan: {num_people}")

        # Extract invite link
        invite_link_element = driver.find_element(By.ID, "invite-link")
        invite_link = invite_link_element.get_attribute("value")
        print(f"Invite link: {invite_link}")

        # Prepare the data to return
        family_data = {
            "user_id": user_id,
            "display_name": display_name,
            "family_address": address,
            "num_people": num_people,
            "invite_link": invite_link,
            "premium_end_date": premium_end_date
        }
        print(f"Debug: family_data = {family_data}")  # Added debug print

        # Update the task status in the database
        task = session.query(Task).filter_by(id=event['task_id']).first()
        if task:
            task.status = 'COMPLETED'
            task.data = json.dumps(family_data)
            print(f"Debug: Updated task status to COMPLETED")  # Added debug print
            
        
            spotify_account = session.query(SpotifyFamilyAccount).filter_by(username=user_id).first()

            task.spotify_family_accountId = spotify_account.id
            print(f"Debug: Set task.spotify_family_accountId to {spotify_account.id}")  # Added debug print
            

            # Create a new FamilyUpdateTaskPayload
            family_update_payload = FamilyUpdateTaskPayload(
                id=str(uuid.uuid4()),
                task_id=event['task_id'],
                username=user_id,
                display_name=display_name,
                physical_address=address,
                number_of_members=num_people,
                invite_link=invite_link,
                status='ACTIVE',  # Assuming the family account is active
                premium_end_date=datetime.fromisoformat(premium_end_date) if premium_end_date != "Not found" else None
            )
            session.add(family_update_payload)
            print(f"Debug: Added new FamilyUpdateTaskPayload to session")  # Added debug print
            
            session.commit()
            print(f"Debug: Committed session")  # Added debug print

        return {
            'statusCode': 200,
            'body': json.dumps(family_data),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except Exception as e:
        saveScreenshotThrowException(driver, s3, "Failed to retrieve family data. Screenshot saved as ", throw=False)
        # Update the task status in the database
        task = session.query(Task).filter_by(id=event['task_id']).first()
        print(e)
        if task:
            task.status = 'FAILED'
            task.error = str(e)
            session.commit()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
            
    finally:
        driver.get('https://www.spotify.com/in-en/logout/')
        print("Logging out")
        time.sleep(0.5)
        driver.quit()
        session.close()