from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium_recaptcha_solver import RecaptchaSolver
from urllib.parse import urlparse
import time
from src.utils.helper import login, update_task_status
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from decimal import Decimal
import random
from src.utils.confirmation_code import get_confirmation_code
from datetime import datetime, timedelta, timezone
from models import Task
from sqlalchemy.orm import Session

def solve_captcha(driver, event, session):
    task_id = event['task_id']
    current_url = driver.current_url
    parsed_url = urlparse(current_url)
    
    if parsed_url.netloc == "challenge.spotify.com":
        update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Detecting challenge type')
        if "email" in parsed_url.path:
            update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Email confirmation challenge detected')
            print("Email confirmation captcha detected")
            handle_email_confirmation(driver, event, session)
        else:
            update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Regular reCAPTCHA detected')
            print("Regular reCAPTCHA detected")
            solver = RecaptchaSolver(driver)
            print("Beginning captcha solving")
            try:
                update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Locating reCAPTCHA iframe')
                recaptcha_iframe = driver.find_element(By.XPATH, '//iframe[@title="reCAPTCHA"]')
                print("Found iframe")
                time.sleep(3)
                update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Attempting to solve reCAPTCHA')
                print("Attempting to solve reCAPTCHA")
                try:
                    solver.click_recaptcha_v2(iframe=recaptcha_iframe)  
                    print("Recaptcha theoretically solved")
                except Exception as e:
                    print(f"Error solving reCAPTCHA, maybe library is outdated: {e}")
                time.sleep(2)

                update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Submitting solved reCAPTCHA')
                done_button = driver.find_element(By.XPATH, '//button[@name="solve"]')
                print("Found done button")
                done_button.click()
                print("Clicked done button")
                time.sleep(2)
                update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'Challenge solved successfully')
            except Exception as e:
                update_task_status(session, task_id, 'SOLVING_CHALLENGE', f'Error solving reCAPTCHA: {str(e)}')
                print(f"Error solving reCAPTCHA: {e}")
    else:
        update_task_status(session, task_id, 'SOLVING_CHALLENGE', 'No challenge detected')
        print("No captcha detected")

def handle_email_confirmation(driver, event, session):
    task_id = event['task_id']
    email = event.get('email', '')

         
    if email.endswith('@sampledomain.com'):
        update_task_status(session, task_id, 'FETCHING_CODE', 'Fetching confirmation code from email')
        start_time = datetime.now(timezone.utc)
        max_wait_time = timedelta(minutes=2)
        
        while datetime.now(timezone.utc) - start_time < max_wait_time:
            code = get_confirmation_code(email)
            if code:
                update_task_status(session, task_id, 'CODE_RECEIVED', 'Confirmation code received from email')
                print(f"Received confirmation code: {code}")
                input_confirmation_code(driver, code, task_id, session)
                return
            else:
                time_left = max_wait_time - (datetime.now(timezone.utc) - start_time)
                update_task_status(session, task_id, 'WAITING_FOR_CODE', f'Waiting for email... {time_left.seconds} seconds left')
                time.sleep(10)  # Wait 10 seconds before trying again
        
        update_task_status(session, task_id, 'ERROR', 'Failed to fetch confirmation code from email within 2 minutes')
        raise Exception("Failed to fetch confirmation code from email within 2 minutes")
    else:
        try:
            update_task_status(session, task_id, 'WAITING_FOR_CODE', 'Waiting for email confirmation code')
            print("Waiting for code....")
            # Poll for TEMP_CODE for up to 5 minutes
            start_time = time.time()
            while time.time() - start_time < 300:  # 300 seconds = 5 minutes
                time_left = 300 - (time.time() - start_time)
                update_task_status(session, task_id, 'WAITING_FOR_CODE', f'Waiting for code... {time_left:.0f} seconds left')
                print(f"Time left to enter the code: {time_left:.2f} seconds")
                
                task = session.query(Task).filter_by(id=task_id).first()
                if task and task.temp_code:
                    code = task.temp_code
                    if isinstance(code, Decimal):
                        code = str(code)
                    if code and len(code) == 6 and code.isdigit():
                        update_task_status(session, task_id, 'CODE_RECEIVED', 'Confirmation code received')
                        print(f"Received confirmation code: {code}")
                        input_confirmation_code(driver, code, task_id, session)
                        return
                time.sleep(5)  # Wait 5 seconds before polling again
            
            update_task_status(session, task_id, 'TIMEOUT', 'Timed out waiting for confirmation code')
            print("Timed out waiting for confirmation code")
            raise Exception("Email confirmation code not received within 5 minutes")
        finally:
            print("")

def input_confirmation_code(driver, code, task_id, session):
    try:
        update_task_status(session, task_id, 'ENTERING_CODE', 'Waiting for input field to be present')
        # Wait for the input field to be present
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "Type the {pinLength}-digit code we sent you to confirm your email"))
        )
        
        # Add a short wait before interacting with the input field
        time.sleep(random.uniform(1.0, 2.0))
        
        update_task_status(session, task_id, 'ENTERING_CODE', 'Entering confirmation code')
        input_field.send_keys(code)
        
        # Add another short wait before clicking the "Next" button
        time.sleep(random.uniform(1.5, 2.5))
        
        update_task_status(session, task_id, 'SUBMITTING_CODE', 'Clicking Next button')
        # Click the "Next" button
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-encore-id='buttonPrimary']"))
        )
        next_button.click()
        
        # Add a final wait after clicking the button
        time.sleep(random.uniform(2.0, 3.0))
        
        update_task_status(session, task_id, 'CODE_SUBMITTED', 'Confirmation code submitted successfully')
        print("Confirmation code submitted successfully")
    except Exception as e:
        update_task_status(session, task_id, 'ERROR', f'Error inputting confirmation code: {str(e)}')
        print(f"Error inputting confirmation code: {e}")
        raise
    finally:
        print("")

def main():
    service = Service('/Users/{username}/chromedriver')
    driver = webdriver.Chrome(service=service)

    # Sample event object for testing
    event = {
        "email": "test@example.com",
        "password": "testpassword"
    }

    solve_captcha(driver, event)

    # Close the browser
    driver.quit()

if __name__ == "__main__":
    main()