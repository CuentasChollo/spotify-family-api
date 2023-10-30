import time
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


def send_keys_naturally(element, text):
    for char in text:
        time.sleep(random.uniform(0.1, 0.3))  # delay between key presses
        element.send_keys(char)

def login(driver, event, s3):
    print("Starting login process")
    driver.get('https://accounts.spotify.com/en/login')
  
    print("Window size: ", driver.get_window_size())
         
    time.sleep(random.uniform(2.0, 3.0))

    loginuser = driver.find_element(By.ID, "login-username")
    send_keys_naturally(loginuser, event['email'])
    time.sleep(random.uniform(1.0, 2.0))

    password = driver.find_element(By.ID, "login-password")
    send_keys_naturally(password, event['password'])
    time.sleep(random.uniform(1.0, 2.0))

    print("Clicking login", driver.current_url)

    enter = driver.find_element(By.ID, 'login-button')
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(enter, 5, 6).click_and_hold().perform()
    time.sleep(0.8)
    actions.release().perform()
    time.sleep(3)
    # While still in login, keep clicking the button
    attempts = 0
    while driver.current_url == "https://accounts.spotify.com/en/login" and attempts < 3:
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(1)
        #Refresh page
        driver.refresh()
        #Insert password again
        password = driver.find_element(By.ID, "login-password")
        send_keys_naturally(password, event['password'])
        time.sleep(1)
        print("Clicking login again", driver.current_url)
        # Create an ActionChains instance
        enter = driver.find_element(By.ID, 'login-button')
        actions = ActionChains(driver) 
        # Move to the button with an offset and click
        actions.move_to_element_with_offset(enter, 10,10).click_and_hold().perform()
        time.sleep(1)
        actions.release().perform()
        attempts += 1
        time.sleep(1)
        if attempts == 2:
            saveScreenshotThrowException(driver, s3, "Failed to login after {} attempts. Screenshot saved as ".format(attempts), throw=True)
        time.sleep(1)

    #If the login button is still there, raise an exception
    if driver.current_url == "https://accounts.spotify.com/en/login":
        raise Exception("Failed to login after ", attempts, " attempts")
    else:
        print("Login successful")


def saveScreenshotThrowException(driver, s3, message="", throw=True):
    screenshot_filename = f"/tmp/screenshot_{time.strftime('%Y%m%d-%H%M%S')}.png"
    driver.save_screenshot(screenshot_filename)
    print(f"Screenshot saved as {screenshot_filename}")
                    
    # Upload the screenshot to S3
    with open(screenshot_filename, "rb") as data:
        s3.upload_fileobj(data, "cc-chromedriver", screenshot_filename)
    
    if throw:
        raise Exception(message + f"Screenshot saved as {screenshot_filename} in S3")
