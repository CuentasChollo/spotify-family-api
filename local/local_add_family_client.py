import random
import time
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from captchasolver import solve_captcha
from urllib.parse import urlparse
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import re
from fake_useragent import UserAgent
from selenium_stealth import stealth

# Import the helper functions
from helper import login, saveScreenshotThrowException, send_keys_naturally

def local_add_family_client(event):
    options = webdriver.ChromeOptions()
    ua = UserAgent()
    userAgent = ua.random

    physicalAddress = event.get('physicalAddress', '123 Main St, City, State, 12345')
    invite_code = event.get('invite_code', 'SAMPLE_INVITE_CODE')
    task_id = event.get('task_id', str(uuid.uuid4()))

    options.add_argument(f'user-agent={userAgent}')
    options.add_argument("--window-size=1280x1696")
    
    # Remove headless mode for local debugging
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1280, 1696)

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print(f"Task {task_id} in progress")

        login(driver, event, None)  # Pass None instead of s3 client

        print("Captcha check")
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Captcha found", driver.current_url)
            solve_captcha(driver, event)  # Pass both driver and event
            time.sleep(2)

        print("Captcha solved | No captcha", driver.current_url)

        print("Going to profile page")
        driver.get('https://www.spotify.com/us/account/profile/')
        print(driver.current_url)

        login_url_pattern = r'https://accounts\.spotify\.com/.*/login'
        max_login_attempts = 3
        login_attempts = 0

        while re.match(login_url_pattern, driver.current_url) and login_attempts < max_login_attempts:
            print(f"Redirected to login page. Attempt {login_attempts + 1} of {max_login_attempts}")
            login(driver, event, None)
            
            print("Navigating back to profile page")
            driver.get('https://www.spotify.com/us/account/profile/')
            time.sleep(5)
            print(f"Current URL: {driver.current_url}")
            
            login_attempts += 1

        if re.match(login_url_pattern, driver.current_url):
            raise Exception("Failed to log in after multiple attempts")

        print(f"Successfully on profile page. Current URL: {driver.current_url}")

        time.sleep(2)
        for i in range(4):
            driver.execute_script("window.scrollTo(0, 500)")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)

        select = Select(driver.find_element(By.ID, 'country'))
        select.select_by_value('IN')
        selectText = select.first_selected_option.text
        driver.execute_script("window.scrollTo(0, 500)")
        print("Scrolling till the end")

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
                    print("Failed to find cookies")
                if i == 0:
                    print("Failed to click submit button")
                    raise e
        
        driver.get('https://www.spotify.com/en/family/join/confirm/' + invite_code)
        driver.get('https://www.spotify.com/en/family/join/address/' + invite_code)

        print("Proceeding to enter address")
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'address')))
        address = driver.find_element(By.ID, 'address')
        address.click()
        time.sleep(1)
        address.send_keys(physicalAddress)
        address.send_keys(u'\ue004')
        address.send_keys(u'\ue007')
        time.sleep(1)
        print("Address entered")

        time.sleep(1)
        confirm = driver.find_element(By.CSS_SELECTOR, "[data-encore-id='buttonPrimary']")
        confirm.click()
        time.sleep(1)
        print("Clicked confirm | Accepted invite")

    except Exception as e:
        print(f"Task {task_id} failed")
        print(str(e))
        return {
            "statusCode": 500,
            "body": str(e)
        }
            
    finally:
        driver.get('https://www.spotify.com/en/logout/')
        print("Logging out")
        time.sleep(0.5)
        driver.quit()

    print(f"Task {task_id} completed")

    response = {
        "statusCode": 200,
        "body": selectText
    }

    return response

if __name__ == "__main__":
    # Sample event object
    event = {
        "email": "francesc@sampledomain.com",
        "password": "abc123",
        "physicalAddress": "123 Main St, City, State, 12345",
        "invite_code": "1234567890",
        "task_id": "local_test_task"
    }

    result = local_add_family_client(event)
    print(result)