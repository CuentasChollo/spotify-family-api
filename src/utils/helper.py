import time
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from PIL import Image, ImageDraw, ImageFont
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

load_dotenv()
# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def update_task_status(session, task_id, status, step_description):
    try:
        task = session.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = status
            task.step_description = step_description
            task.updated_at = datetime.now(timezone.utc)
            session.commit()
    except Exception as e:
        print(f"Error updating task status: {str(e)}")
        session.rollback()

def send_keys_naturally(element, text):
    for char in text:
        time.sleep(random.uniform(0.1, 0.3))  # delay between key presses
        element.send_keys(char)

def login(driver, event, s3):
    print("Starting login process")
    session = Session()
    update_task_status(session, event['task_id'], 'LOGGING_IN', 'Navigating to login page')
    driver.get('https://accounts.spotify.com/en/login')
  
    print("Window size: ", driver.get_window_size())
         
    time.sleep(random.uniform(2.0, 3.0))

    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        try:
            update_task_status(session, event['task_id'], 'LOGGING_IN', f'Entering credentials (Attempt {attempts + 1})')
            loginuser = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-username")))
            loginuser.clear()  # Clear the username field before typing
            send_keys_naturally(loginuser, event['email'])
            time.sleep(random.uniform(2.0, 3.1))

            password = driver.find_element(By.ID, "login-password")
            send_keys_naturally(password, event['password'])
            time.sleep(random.uniform(1.0, 2.0))

            print(f"Clicking login (Attempt {attempts + 1})", driver.current_url)

            update_task_status(session, event['task_id'], 'LOGGING_IN', f'Submitting login form (Attempt {attempts + 1})')
            enter = driver.find_element(By.ID, 'login-button')
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(enter, 5, 6).click_and_hold().perform()
            time.sleep(0.3)
            actions.release().perform()
            
            # Wait for the page to change or for an error to appear
            WebDriverWait(driver, 20).until(lambda d: d.current_url != "https://accounts.spotify.com/en/login" or d.find_elements(By.CSS_SELECTOR, "svg[aria-label='Error:']"))
            
            # Check for password error message
            error_svg = driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Error:']")
            if error_svg:
                next_element = error_svg[0].find_element(By.XPATH, "following-sibling::*[1]")
                if next_element and "password" in next_element.text.lower():
                    update_task_status(session, event['task_id'], 'WRONG_PASSWORD', 'Incorrect password provided')
                    return False  # Indicate login failure due to wrong password
            
            if driver.current_url == "https://accounts.spotify.com/en/login":
                raise Exception("Login page did not change, retrying...")
            
            print("Login successful. Current url: ", driver.current_url)
            
            update_task_status(session, event['task_id'], 'LOGGED_IN', 'Successfully logged in')
            return True  # Indicate successful login
        
        except Exception as e:
            print(f"Login error (Attempt {attempts + 1}): {str(e)}")
            attempts += 1
            if attempts >= max_attempts:
                update_task_status(session, event['task_id'], 'LOGIN_FAILED', f'Unable to log in after {max_attempts} attempts')
                saveScreenshotThrowException(driver, s3, f"Login failed after {max_attempts} attempts: {str(e)}. Screenshot saved as ", throw=True)
            else:
                time.sleep(random.uniform(2.0, 4.0))  # Wait before retrying
                driver.refresh()  # Refresh the page before the next attempt

    return False  # Indicate login failure after all attempts

def saveScreenshotThrowException(driver, s3, message="", throw=True):
    screenshot_filename = f"/tmp/screenshot_{time.strftime('%Y%m%d-%H%M%S')}.png"
    driver.save_screenshot(screenshot_filename)
    print(f"Screenshot saved as {screenshot_filename}")
    
    # Open the screenshot with PIL
    img = Image.open(screenshot_filename)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    
    # Add the URL to the image
    url = driver.current_url
    draw.text((10, 10), url, font=font, fill=(255, 0, 0))
    
    # Save the modified image
    img.save(screenshot_filename)
                    
    # Upload the screenshot to S3
    with open(screenshot_filename, "rb") as data:
        s3.upload_fileobj(data, "cc-chromedriver", screenshot_filename)
    
    if throw:
        raise Exception(message + f"Screenshot saved as {screenshot_filename} in S3")