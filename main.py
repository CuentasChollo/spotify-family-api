from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import random

def main():
    # Set the path for the chromedriver executable
    

    # Initialize the Chrome driver
    # Note: Ensure that you have downloaded the correct driver for the version of Chrome installed on your system.
    driver = webdriver.Chrome()

    try:
        driver.get('https://accounts.spotify.com/en/login')
        loginuser = driver.find_element(value='login-username')
        loginuser.send_keys('matvetron@gmail.com')
        time.sleep(random.uniform(2.0, 3.0))
        password = driver.find_element(value='login-password')
        password.send_keys('Upgrademyspoty1')
        time.sleep(random.uniform(2.0, 3.1))
        enter = driver.find_element(value='login-button')
        enter.click()
        time.sleep(random.uniform(1.0, 2.0))
        accountsettings = driver.find_element(value='account-settings-link')
        accountsettings.click()
        time.sleep(2)
        account_widget = driver.find_element(by="css selector", value="[data-testid='account-widget']")
        account_widget.click()
        time.sleep(2)

        driver.get('https://www.spotify.com/es/account/family/')
        time.sleep(2)

        cookies = driver.find_element(by=By.ID, value='onetrust-accept-btn-handler')
        cookies.click()
        time.sleep(2)

        #scroll a bit
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(2)


        driver.switch_to.frame(0)  # switch to the first iframe
        #list = driver.find_elements(By.XPATH, "//ul[@role='list']//li[@data-encore-id='type']")
        list2 = driver.find_elements(By.XPATH, "//ul[@role='list']//li//button")
        #list3 = driver.find_elements(By.CSS_SELECTOR, ".home-hub-icon-avatar")
        #number3 = len(list3)
        #number = len(list)
        number2 = len(list2)

        
        print(number2)
        # OPTIONAL: Retrieve and print the results
        # This part depends on the structure of the result page, you'd need to inspect the elements for precise navigation.
        # results = driver.find_elements_by_class_name('your-result-element-class')
        # for result in results:
        #     print(result.text)

    except Exception as e:
        print(e)
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    main()
