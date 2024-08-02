from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium_recaptcha_solver import RecaptchaSolver
from selenium.webdriver.chrome.service import Service
from urllib.parse import urlparse
import time
from helper import login

def solve_captcha(driver, event):
    current_url = driver.current_url
    parsed_url = urlparse(current_url)
    
    if parsed_url.netloc == "challenge.spotify.com":
        if "email" in parsed_url.path:
            print("Email confirmation captcha detected")
            driver.get('https://accounts.spotify.com/en/login')
            time.sleep(20)  # Wait for page to load
            driver.refresh()
            time.sleep(3)  # Wait after refresh
            login(driver, event, None)  # Re-execute login
        else:
            print("Regular reCAPTCHA detected")
            solver = RecaptchaSolver(driver)
            print("Beginning captcha solving")
            try:
                recaptcha_iframe = driver.find_element(By.XPATH, '//iframe[@title="reCAPTCHA"]')
                print("Found iframe")
                time.sleep(2.1)
                solver.click_recaptcha_v2(iframe=recaptcha_iframe)  
                print("Clicked recaptcha")
                time.sleep(2)

                done_button = driver.find_element(By.XPATH, '//button[@name="solve"]')
                print("Found done button")
                done_button.click()
                print("Clicked done button")
                time.sleep(2)
            except Exception as e:
                print(f"Error solving reCAPTCHA: {e}")
    else:
        print("No captcha detected")

def main():
    service = Service('/Users/matveydergunov/chromedriver')
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