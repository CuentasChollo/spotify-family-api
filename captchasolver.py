
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium_recaptcha_solver import RecaptchaSolver
from selenium.webdriver.chrome.service import Service

import time

def solve_captcha(driver):
    solver = RecaptchaSolver(driver)
    try:
        recaptcha_iframe = driver.find_element(By.XPATH, '//iframe[@title="reCAPTCHA"]')

        time.sleep(2)
        solver.click_recaptcha_v2(iframe=recaptcha_iframe)  

        time.sleep(2)

        done_button = driver.find_element(By.XPATH, '//button[@name="solve"]')

        done_button.click()

        time.sleep(2)
    except Exception as e:
        print(e)

def main():

    service = Service('/Users/matveydergunov/chromedriver')
    driver = webdriver.Chrome(service=service)

    solve_captcha(driver)

    # Close the browser
    driver.quit()

if __name__ == "__main__":
    main()