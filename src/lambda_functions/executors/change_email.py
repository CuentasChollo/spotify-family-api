import datetime
import random
import time
import uuid
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from src.utils.challenge_solver import solve_captcha
from urllib.parse import urlparse
from tempfile import mkdtemp
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from src.utils.helper import login, saveScreenshotThrowException, update_task_status
from selenium_stealth import stealth
from fake_useragent import UserAgent
import boto3
import requests
import re
import json
import datetime
from models import Task, SpotifyFamilyAccount
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from selenium.webdriver.common.keys import Keys


"""
- email
- password
- new_email
- task_id
"""

def change_email(event, context):
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

        print("Going to account overview page")
        driver.get('https://www.spotify.com/us/account/overview/')
        print(driver.current_url)

        # Spend some time on the account overview page
        time.sleep(random.uniform(3, 5))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(random.uniform(1, 2))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 3))
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(1, 2))

        print("Now navigating to profile page")
        driver.get('https://www.spotify.com/us/account/profile/')
        print(driver.current_url)

        login_url_pattern = r'https://accounts\.spotify\.com/.*/login'
        max_login_attempts = 3
        login_attempts = 0

        while re.match(login_url_pattern, driver.current_url) and login_attempts < max_login_attempts:
            print(f"Redirected to login page. Attempt {login_attempts + 1} of {max_login_attempts}")
            login(driver, event, s3)
            
            # Check again if the login was successful
            with SessionLocal() as session:
                task = session.query(Task).filter(Task.id == event['task_id']).first()
                current_status = task.status if task else None
                if current_status == 'WRONG_PASSWORD':
                    update_task_status(session, event['task_id'], 'FAILED', 'Login failed due to incorrect password')
                    return {
                        "statusCode": 400,
                        "body": "Login failed: Incorrect password"
                    }
            
            # Check if redirected to challenge page
            if urlparse(driver.current_url).netloc == "challenge.spotify.com":
                print("Challenge found", driver.current_url)
                solve_captcha(driver, event)
                time.sleep(2)
                print("Challenge solved", driver.current_url)
            
            print("Navigating back to profile page. From: ", driver.current_url)
            driver.get('https://www.spotify.com/us/account/profile/')
            time.sleep(5)
            print(f"Current URL: {driver.current_url}")
            
            login_attempts += 1

        if re.match(login_url_pattern, driver.current_url):
            raise Exception("Failed to log in after multiple attempts")

        print(f"Successfully on profile page. Current URL: {driver.current_url}")

        time.sleep(random.uniform(2, 3))
        for i in range(3):
            driver.execute_script(f"window.scrollTo(0, {random.randint(300, 700)});")
            time.sleep(random.uniform(0.5, 1))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1))

        try:
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-encore-id='formInput'][id='email']"))
            )
            # Click the email field
            email_input.click()
            time.sleep(random.uniform(0.5, 1))
            # Empty the field using Ctrl+A and Backspace
            email_input.send_keys(Keys.CONTROL + "a")
            time.sleep(random.uniform(0.5, 1))
            email_input.send_keys(Keys.BACKSPACE)
            
            # Simulate natural typing for new email
            for char in event['new_email']:
                email_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            print(f"Entered new email: {event['new_email']}")

            # Enter password
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-encore-id='formInput'][id='password']"))
            )
            password_input.clear()
            for char in event['password']:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            print("Entered password")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            for i in range(4):
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[type='submit']")))
                    save = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(save, 5, 6).click_and_hold().perform()
                    time.sleep(random.uniform(0.5, 1))
                    actions.release().perform()
                    time.sleep(random.uniform(0.5, 1))
                    print("Clicked save")
                    break
                except Exception as e:
                    print("Attempt", i+1, "failed. Trying to click cookies and retry.")
                    try:
                        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
                        cookies = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
                        cookies.click()
                        time.sleep(random.uniform(1, 2))
                    except:
                        saveScreenshotThrowException(driver, s3, "Failed to find cookies after 4 attempts. Screenshot saved as ")
                    if i == 3:
                        print("Failed to click submit button after 4 attempts")
                        raise e
            
            time.sleep(random.uniform(2, 3))  # Wait for changes to be saved

            # Update the email in the database
            family_account = session.query(SpotifyFamilyAccount).filter_by(email=event['email']).first()
            if family_account:
                family_account.past_emails.append(family_account.email)
                family_account.email = event['new_email']
                session.commit()
                print(f"Updated email in database from {event['email']} to {event['new_email']}")

            # Update task status
            task = session.query(Task).filter_by(id=event['task_id']).first()
            if task:
                task.status = 'COMPLETED'
                task.updated_at = datetime.datetime.now(datetime.timezone.utc)
                session.commit()
                print(f"Updated task status to COMPLETED")

            return {
                'statusCode': 200,
                'body': json.dumps('Email updated successfully')
            }

        except Exception as e:
            print(f"Failed to change email: {str(e)}")
            saveScreenshotThrowException(driver, s3, "Failed to change email. Screenshot saved as ")

            # Update task status to FAILED
            task = session.query(Task).filter_by(id=event['task_id']).first()
            if task:
                task.status = 'FAILED'
                task.error = str(e)
                task.updated_at = datetime.datetime.now(datetime.timezone.utc)
                session.commit()
                print(f"Updated task status to FAILED")

            return {
                'statusCode': 500,
                'body': json.dumps('Failed to update email')
            }

    finally:
        driver.get('https://www.spotify.com/en/logout/')
        print("Logging out")
        time.sleep(random.uniform(0.5, 1))
        driver.quit()
        session.close()  # Close the session
