import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from captchasolver import solve_captcha
from urllib.parse import urlparse
from tempfile import mkdtemp
from helper import login, send_keys_naturally
import boto3
import time
from selenium_stealth import stealth


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

    #selenium_stealth options
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

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
        login(driver, event, s3)
        # Check if the current URL is challenge.spotify.com
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Captcha found", driver.current_url)
            solve_captcha(driver)  # Call the solve_captcha function
            time.sleep(3)

        print("Catcha solved | No captcha", driver.current_url)
        #if driver.current_url != "https://www.spotify.com/es/account/overview/":
            #raise Exception(driver.current_url)

    
        driver.get('https://www.spotify.com/es/account/family/')
        time.sleep(2)
        print("Clicking manage", driver.current_url)
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
        driver.get('https://www.spotify.com/en/logout/')
        print("Logging out")
        time.sleep(1)
        driver.quit()

    response = {
        "statusCode": 200,
        "body": number2
    }

    return response