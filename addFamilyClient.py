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
from helper import login, saveScreenshotThrowException, send_keys_naturally
from selenium_stealth import stealth


def add_family_client(event, context):
    options = webdriver.ChromeOptions()
    #service = webdriver.ChromeService("/opt/chromedriver")

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

    driver = webdriver.Chrome('/opt/chromedriver', options=options)
    driver.set_window_size(1280, 1696)
    s3 = boto3.client('s3')

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

        login(driver, event, s3)
        
        # Check if the current URL is challenge.spotify.com
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Captcha found", driver.current_url)
            solve_captcha(driver)  # Call the solve_captcha function
            time.sleep(2)

        print("Catcha solved", driver.current_url)
        #if driver.current_url != "https://www.spotify.com/es/account/overview/":
            #raise Exception(driver.current_url)

        driver.get('https://www.spotify.com/us/account/profile/')
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
        
        #https://www.spotify.com/es/family/join/invite/76yA3B1Xc2A6433/ transform to https://www.spotify.com/es/family/join/confirm/76yA3B1Xc2A6433/
        #The argumetnt is event['invite']
        driver.get('https://www.spotify.com/en/family/join/confirm/' + event['invite'])

        driver.get('https://www.spotify.com/en/family/join/address/' + event['invite'])

        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'address')))
        address = driver.find_element(By.ID, 'address')
        address.click()
        time.sleep(1)
        address.send_keys("Tombs of the Kings Ave 63, Chloraka, Cyprus")

        submit = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
        submit.click()
        time.sleep(1)
        confirm = driver.find_element(By.CSS_SELECTOR, "[data-encore-id='buttonPrimary']")
        confirm.click()
        time.sleep(1)
        print("Clicked confirm | Accepted invite")


    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
         }
            
    finally:
        driver.get('https://www.spotify.com/en/logout/')
        print("Logging out")
        time.sleep(0.5)
        driver.quit()
        
    response = {
            "statusCode": 200,
            "body": selectText
        }

    return response
    


