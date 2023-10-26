import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from captchasolver import solve_captcha
from urllib.parse import urlparse
from tempfile import mkdtemp

import time

def lambda_handler(event, context):
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

    try:
        driver.get('https://accounts.spotify.com/en/login')
        loginuser = driver.find_element(By.ID, "login-username")
        loginuser.send_keys('matvetron@gmail.com')
        password = driver.find_element(By.ID, "login-password")
        password.send_keys('Upgrademyspoty1')
        time.sleep(2)
        print("Clicking login")
        enter = driver.find_element(By.ID, 'login-button')
        enter.click()
        time.sleep(2)
        
        # Check if the current URL is challenge.spotify.com
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            solve_captcha(driver)  # Call the solve_captcha function
            time.sleep(2)


        #if driver.current_url != "https://www.spotify.com/es/account/overview/":
            #raise Exception(driver.current_url)

        driver.get('https://www.spotify.com/es/account/family/')
        time.sleep(2)

        #cookies = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
        #cookies.click()
        #time.sleep(2)

        #scroll a bit
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(2)

        driver.switch_to.frame(0)  # switch to the first iframe
        list2 = driver.find_elements(By.XPATH, "//ul[@role='list']//li//button")
        number2 = len(list2)

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
        "body": number2
    }

    return response