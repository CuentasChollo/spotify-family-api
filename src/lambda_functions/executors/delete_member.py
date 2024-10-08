import random
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
from tempfile import mkdtemp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import boto3
from selenium_stealth import stealth
from fake_useragent import UserAgent
import json
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task, SpotifyFamilyAccount, SpotifyFamilySpotPeriod
from src.utils.helper import login, saveScreenshotThrowException
from src.utils.challenge_solver import solve_captcha
from datetime import datetime, timezone

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

"""
spotify_member_id: ID of the member to be removed
email: Email of the family
password: Password of the family
task_id: ID of the task
after_trial: Boolean? //Default false
"""
def delete_member(event, context):
    print("Starting delete_member function")
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
    
    print("Initializing Chrome driver")
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
        spotify_member_id = event['spotify_member_id']
        email = event['email']
        password = event['password']
        after_trial = event['after_trial']
        task_id = event['task_id']
      
        print(f"Deleting member with ID: {spotify_member_id}")
        # Login to Spotify
        print("Attempting to log in")
        login(driver, event, s3)

        # Check for captcha
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Challenge found", driver.current_url)
            solve_captcha(driver, event, session)
            time.sleep(2)

        print("Challenge solved", driver.current_url)
        saveScreenshotThrowException(driver, s3, "Challenge solved", throw=False)

        # Extract premium end date
        print("Navigating to account overview page...")
        driver.get('https://www.spotify.com/in-en/account/overview/')
        time.sleep(5)  # Give the page some time to load

        # Navigate to the specific member's page
        print(f"Navigating to member page: https://www.spotify.com/in-en/account/family/member/{spotify_member_id}/")
        driver.get(f"https://www.spotify.com/in-en/account/family/member/{spotify_member_id}/")
        time.sleep(5)

        if not driver.current_url.startswith(f"https://www.spotify.com/in-en/account/family/member/{spotify_member_id}/"):
            raise Exception(f"Failed to navigate to member page. Current URL: {driver.current_url}")


        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "family-web-iframe")))
        print("Switched to iframe")

        # Click on "Remove from plan" button
        print("Attempting to click 'Remove from plan' button")
        remove_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-encore-id='buttonSecondary']"))
        )
        remove_button.click()

        # Click on confirm remove button
        print("Attempting to click confirm remove button")
        confirm_remove_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-encore-id='buttonPrimary']"))
        )
        confirm_remove_button.click()

        # Wait for 6 seconds and check if we're back at the family page
        time.sleep(6)
        print(f"Current URL after removal: {driver.current_url}")
        if driver.current_url != "https://www.spotify.com/in-en/account/family/":
            raise Exception("Failed to remove member. Not redirected to family page.")

        # Fetch the updated members list
        print("Fetching updated members list")
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
        updated_members = driver.execute_script(script)
        print(f"Updated members: {json.dumps(updated_members, indent=2)}")

        # Verify that the member is no longer in the list
        if any(member['id'] == spotify_member_id for member in updated_members['members']):
            raise Exception(f"Member with ID {spotify_member_id} is still in the family plan.")

        # Update SpotifyFamilySpotPeriod status
        spot_period = session.query(SpotifyFamilySpotPeriod).filter(
            SpotifyFamilySpotPeriod.spotify_member_id == spotify_member_id,
            SpotifyFamilySpotPeriod.status.in_(['ACTIVE', 'GRACE_PERIOD'])
        ).first()

        if spot_period:
            if after_trial:
                spot_period.status = 'GRACE_PERIOD'  
            else:
                spot_period.status = 'EXPIRED'
            session.commit()

        # Update task status
        print("Updating task status")
        task = session.query(Task).filter_by(id=event['task_id']).first()
        if task:
            task.status = 'COMPLETED'
            task.data = json.dumps(updated_members)
            session.commit()

        print("Member removal successful")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f"Successfully removed member with ID {spotify_member_id} from family plan"}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        saveScreenshotThrowException(driver, s3, "Failed to delete family member. Screenshot saved as ", throw=False)
        # Update the task status in the database
        task = session.query(Task).filter_by(id=event['task_id']).first()
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
        print("Logging out and closing the browser")
        driver.get('https://www.spotify.com/in-en/logout/')
        time.sleep(0.5)
        driver.quit()
        session.close()