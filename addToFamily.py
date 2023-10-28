import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from captchasolver import solve_captcha
from urllib.parse import urlparse
from tempfile import mkdtemp
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import boto3
from aux import *



def add_to_family(event, context):
    options = webdriver.ChromeOptions()
    #service = webdriver.ChromeService("/opt/chromedriver")

    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1024x768")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")

    driver = webdriver.Chrome('/opt/chromedriver', options=options)
    driver.set_window_size(1024, 768)
    s3 = boto3.client('s3')
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        driver.get('https://accounts.spotify.com/en/login')
  
        print("Window size: ", driver.get_window_size())
         
        time.sleep(random.uniform(2.0, 3.0))

        loginuser = driver.find_element(By.ID, "login-username")
        send_keys_naturally(loginuser, event['email'])
        time.sleep(random.uniform(2.0, 3.0))

        password = driver.find_element(By.ID, "login-password")
        send_keys_naturally(password, event['password'])
        time.sleep(random.uniform(2.0, 3.0))

        print("Clicking login", driver.current_url)

        enter = driver.find_element(By.ID, 'login-button')
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(enter, 5, 6).click().perform()
        time.sleep(4)
        # While still in login, keep clicking the button
        attempts = 0
        while driver.current_url == "https://accounts.spotify.com/en/login" and attempts < 3:
            driver.execute_script("window.scrollTo(0, 500)")
            time.sleep(4)
            print("Clicking login again", driver.current_url)
            # Create an ActionChains instance
            actions = ActionChains(driver) 
            # Move to the button with an offset and click
            actions.move_to_element_with_offset(enter, 10,10).click().perform()
            attempts += 1
            time.sleep(1)
            if attempts == 2:
                saveScreenshotThrowException(driver, s3, "Failed to login after {} attempts. Screenshot saved as ".format(attempts), throw=True)
            time.sleep(1)

        #If the login button is still there, raise an exception
        if driver.current_url == "https://accounts.spotify.com/en/login":
            raise Exception("Failed to login after ", attempts, " attempts")
        
        # Check if the current URL is challenge.spotify.com
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Captcha found", driver.current_url)
            solve_captcha(driver)  # Call the solve_captcha function
            time.sleep(3)

        print("Catcha solved", driver.current_url)
        #if driver.current_url != "https://www.spotify.com/es/account/overview/":
            #raise Exception(driver.current_url)

        driver.get('https://www.spotify.com/us/account/profile/')
        time.sleep(2)
        #Scroll down and up 4 times in a smooth way
        for i in range(4):
            driver.execute_script("window.scrollTo(0, 500)")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(1)

        print("Trying to click cookies")
        for i in range(5):
            try:
                WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
                cookies = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
                driver.execute_script("window.scrollTo(0, 500)")
                print("Proceeding to click cookies")
                cookies.click()
                print("Clicked cookies")
                time.sleep(2)
                break
            except:
                print("Attempt", i+1, "failed. Trying again.")
                if i == 4:
                    print("Seems that there is no cookies")
                    saveScreenshotThrowException(driver, s3, "Failed to find cookies after 10 attempts. Screenshot saved as ", throw=False)
        #Change in the selector country to value=IN
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
                time.sleep(2)
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

    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
         }
            
    finally:
        # Close the browser
        driver.quit()
        
    response = {
            "statusCode": 200,
            "body": selectText
        }

    return response
    



def saveScreenshotThrowException(driver, s3, message="", throw=True):
    print("Seems that there are no cookies")
    screenshot_filename = f"/tmp/screenshot_{time.strftime('%Y%m%d-%H%M%S')}.png"
    driver.save_screenshot(screenshot_filename)
    print(f"Screenshot saved as {screenshot_filename}")
                    
    # Upload the screenshot to S3
    with open(screenshot_filename, "rb") as data:
        s3.upload_fileobj(data, "cc-chromedriver", screenshot_filename)
                    
    raise Exception(message + f"Screenshot saved as {screenshot_filename} in S3")
