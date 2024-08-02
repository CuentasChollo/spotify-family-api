import random
import time
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from challengeSolver import solve_captcha  # Change this line
from urllib.parse import urlparse
from tempfile import mkdtemp
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import boto3
from helper import login, saveScreenshotThrowException, send_keys_naturally, update_task_status
from selenium_stealth import stealth
from fake_useragent import UserAgent
import re

tasks_table = boto3.resource('dynamodb').Table('tasks')

def add_family_client(event, context):
    options = webdriver.ChromeOptions()
    #service = webdriver.ChromeService("/opt/chromedriver")
    ua = UserAgent()
    userAgent = ua.random


    physicalAddress = event['physicalAddress']
    invite_link = event['inviteLink']
    #email = event['email']
    #password = event['password']
    task_id = event['task_id']

    tasks_table.update_item(
        Key={'task_id': task_id},
        UpdateExpression="set status_string = :s",
        ExpressionAttributeValues={
            ':s': 'INITIATED'
        }
    )

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

    #dynamodb = boto3.client('s3')
    #table = dynamodb.Table('tasks')
    #task_id = str(uuid.uuid4())
    #table.put_item(Item={'task_id': task_id, 'status': 'IN_PROGRESS'})


    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        update_task_status(task_id, 'INITIALIZING', 'Setting up the browser')
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        update_task_status(task_id, 'LOGGING_IN', 'Attempting to log in')
        login(driver, event, s3)

        update_task_status(task_id, 'SOLVING_CAPTCHA', 'Checking for solving any captchas')
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Challenge found", driver.current_url)
            solve_captcha(driver, event)  # Change this line
            time.sleep(2)

        print("Challenge solved", driver.current_url)

        update_task_status(task_id, 'NAVIGATING', 'Navigating to profile page')
        print("Going to profile page")
        driver.get('https://www.spotify.com/us/account/profile/')
        print(driver.current_url)

        
        
        ## BEING ASKED TO LOGIN AFTER SOLVING CAPTCHA
        login_url_pattern = r'https://accounts\.spotify\.com/.*/login'
        max_login_attempts = 3
        login_attempts = 0

        while re.match(login_url_pattern, driver.current_url) and login_attempts < max_login_attempts:
            print(f"Redirected to login page. Attempt {login_attempts + 1} of {max_login_attempts}")
            login(driver, event, s3)
            
            # After login, navigate back to the profile page
            print("Navigating back to profile page")
            driver.get('https://www.spotify.com/us/account/profile/')
            time.sleep(5)  # Wait for page to load
            print(f"Current URL: {driver.current_url}")
            
            login_attempts += 1

        if re.match(login_url_pattern, driver.current_url):
            raise Exception("Failed to log in after multiple attempts")

        print(f"Successfully on profile page. Current URL: {driver.current_url}")



        time.sleep(2)
        #Scroll down and up 4 times in a smooth way
        for i in range(4):
            driver.execute_script("window.scrollTo(0, 500)")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)

        # Commented out the following block as per instructions
        # print("Trying to click cookies")
        # for i in range(5):
        #     try:
        #         WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
        #         cookies = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
        #         driver.execute_script("window.scrollTo(0, 500)")
        #         print("Proceeding to click cookies")
        #         cookies.click()
        #         print("Clicked cookies")
        #         time.sleep(2)
        #         break
        #     except:
        #         print("Attempt", i+1, "failed. Trying again.")
        #         if i == 4:
        #             print("Seems that there is no cookies")
        #             saveScreenshotThrowException(driver, s3, "Failed to find cookies after 10 attempts. Screenshot saved as ", throw=False)


                    
        #Change in the selector country to value=IN
        update_task_status(task_id, 'UPDATING_PROFILE', 'Updating profile information')
        select = Select(driver.find_element(By.ID, 'country'))
        select.select_by_value('IN')
        selectText = select.first_selected_option.text
        #Scroll till the end
        driver.execute_script("window.scrollTo(0, 500)")
        print("Scrolling till the end")


        #Click save on the button type=submit
        for i in range(1):
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[type='submit']")))
                save = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
                save.click()
                time.sleep(1)
                print("Clicked save")
                break
            except Exception as e:
                print("Attempt", i+1, "failed. Trying to click cookies and retry.")
                try:
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
                    cookies = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
                    cookies.click()
                    time.sleep(2)
                except:
                    saveScreenshotThrowException(driver, s3, "Failed to find cookies after 10 attempts. Screenshot saved as ")
                if i == 9:
                    print("Failed to click submit button after 10 attempts")
                    raise e
      
        # ... (previous code remains unchanged until the family joining part)

        update_task_status(task_id, 'JOINING_FAMILY', 'Joining family plan')
        confirm_link = invite_link.replace('/invite/', '/confirm/')
        driver.get(confirm_link)
        print(f'Navigating to confirm page: {confirm_link}')

        address_link = invite_link.replace('/join/invite/', '/join/address/')
        driver.get(address_link)
        print(f'Navigating to address page: {address_link}')

        update_task_status(task_id, 'ENTERING_ADDRESS', 'Entering family address')
        print("Proceeding to enter address")
        saveScreenshotThrowException(driver, s3, "Pre address ", throw=False)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'address')))
        address = driver.find_element(By.ID, 'address')
        address.click()
        time.sleep(1)
        address.send_keys(physicalAddress)
        address.send_keys(u'\ue004')
        address.send_keys(u'\ue007')
        time.sleep(1)
        print("Address entered")

        #saveScreenshotThrowException(driver, s3, "Address entered. Screenshot saved as ", throw=False)
        #submit = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
        #submit.click()
        time.sleep(random.uniform(1, 1.5))
        saveScreenshotThrowException(driver, s3, "Clicked submit. Screenshot saved as ", throw=False)
        update_task_status(task_id, 'CONFIRMING', 'Confirming family plan join')
        confirm = driver.find_element(By.CSS_SELECTOR, "[data-encore-id='buttonPrimary']")
        confirm.click()
        time.sleep(random.uniform(1, 1.5))
        saveScreenshotThrowException(driver, s3, "Clicked confirm. Screenshot saved as ", throw=False)
        print("Clicked confirm | Accepted invite")


    except Exception as e:
        update_task_status(task_id, 'FAILED', f'Error: {str(e)}')
        saveScreenshotThrowException(driver, s3, "Failed to add client. Screenshot saved as ", throw=False)
        return {
            "statusCode": 500,
            "body": str(e)
         }
            
    finally:
        update_task_status(task_id, 'LOGGING_OUT', 'Logging out and cleaning up')
        driver.get('https://www.spotify.com/en/logout/')
        print("Logging out")
        time.sleep(0.5)
        driver.quit()
        

    update_task_status(task_id, 'COMPLETED', 'Successfully joined family plan')

    response = {
            "statusCode": 200,
            "body": selectText
        }

    return response