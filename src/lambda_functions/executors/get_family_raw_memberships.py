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



"""Inputs
- event: {
    "task_id": "123",
    "email": "test@example.com",
    "password": "password123"
}
"""
def get_family_raw_memberships(event, context):
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


        ## Get family memberships 
         # Retrieve all family members' information
        script = """
        async function getFamilyMembersInfo() {
            const response = await fetch('https://www.spotify.com/api/family/v1/family/home/');
            const data = await response.json();
            return {
                members: data.members.map(member => ({
                    id: member.id,
                    name: member.name,
                    isLoggedInUser: member.isLoggedInUser
                })),
                homeId: data.homeId
            };
        }
        return getFamilyMembersInfo();
        """
        members = driver.execute_script(script)

        print(f"Debug: members = {members}")  # Added debug print

        # Update the task status in the database
        task = session.query(Task).filter_by(id=event['task_id']).first()
        if task:
            task.status = 'COMPLETED'
            task.data = json.dumps(members)
            print(f"Debug: Updated task status to COMPLETED")  # Added debug print
            
        
            spotify_account = session.query(SpotifyFamilyAccount).filter_by(email=event['email']).first()

            task.spotify_family_accountId = spotify_account.id
            print(f"Debug: Set task.spotify_family_accountId to {spotify_account.id}")  # Added debug print
            
            session.commit()
            print(f"Debug: Committed session")  # Added debug print

        return {
            'statusCode': 200,
            'body': json.dumps(members),
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