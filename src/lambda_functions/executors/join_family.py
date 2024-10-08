import datetime
import random
import time
import uuid
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from src.utils.challenge_solver import solve_captcha
from urllib.parse import urlparse
from tempfile import mkdtemp
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from src.utils.helper import login, saveScreenshotThrowException, update_task_status
from selenium_stealth import stealth
from fake_useragent import UserAgent
import boto3
import requests
import re
import json

from models import ActivationKey, Task, OrderLine, SpotifyFamilyAccount, SpotifyFamilySpotPeriod, SpotifyIndividualAccount, ShopOrder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables
load_dotenv()

# Create engine and session
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Add this at the beginning of the file with other imports
client = boto3.client('stepfunctions')

# For now the trial duration will be 45 minutes from the time the account was created
TRIAL_DURATION = 45 * 60  # 45 minutes in seconds
GRACE_PERIOD = 24 * 60 * 60  # 1 day in seconds

"""
- email
- password
- physical_address
- invite_link
- task_id
- family_account_id
- activation_key_value
- is_trial: boolean
- customer_id: string (optional, defaults to None) //This value is mandatory if its trial
"""
def join_family(event, context):
    options = webdriver.ChromeOptions()
    ua = UserAgent()
    userAgent = ua.random

    physical_address = event['physical_address']
    invite_link = event['invite_link']
    task_id = event['task_id']
    activation_key_value = event.get('activation_key_value')
    family_account_id = event['family_account_id']
    email = event['email']
    password = event['password']
    is_trial = event.get('is_trial', False)
    customer_id = event.get('customer_id')
    # Initialize task status
    with SessionLocal() as session:
        update_task_status(session, task_id, 'IN_PROGRESS', 'Starting the process')

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

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        print("Initializing the browser")
        with SessionLocal() as session:
            update_task_status(session, task_id, 'INITIALIZING', 'Setting up the browser')
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        with SessionLocal() as session:
            update_task_status(session, task_id, 'LOGGING_IN', 'Attempting to log in')
        login_successful = login(driver, event, s3)

        if not login_successful:
            with SessionLocal() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                current_status = task.status if task else None
                if current_status == 'WRONG_PASSWORD':
                    return {
                        "statusCode": 400,
                        "body": "Login failed: Incorrect password"
                    }
                else:
                    return {
                        "statusCode": 400,
                        "body": "Login failed: Unknown error"
                    }

        # Check if the login was successful
        with SessionLocal() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            current_status = task.status if task else None
            if current_status == 'WRONG_PASSWORD':
                update_task_status(session, task_id, 'FAILED', 'Login failed due to incorrect password')
                return {
                    "statusCode": 400,
                    "body": "Login failed: Incorrect password"
                }

        with SessionLocal() as session:
            update_task_status(session, task_id, 'SOLVING_CAPTCHA', 'Checking for solving any captchas')
        if urlparse(driver.current_url).netloc == "challenge.spotify.com":
            print("Challenge found", driver.current_url)
            with SessionLocal() as session:
                solve_captcha(driver, event, session)
            time.sleep(2)

        print("Challenge solved", driver.current_url)

        with SessionLocal() as session:
            update_task_status(session, task_id, 'NAVIGATING', 'Navigating to profile page')
        print("Going to profile page")
        driver.get('https://www.spotify.com/us/account/profile/')
        print(driver.current_url)

        login_url_pattern = r'https://accounts\.spotify\.com/.*/login'
        max_login_attempts = 3
        login_attempts = 0

        while re.match(login_url_pattern, driver.current_url) and login_attempts < max_login_attempts:
            print(f"Redirected to login page. Attempt {login_attempts + 1} of {max_login_attempts}")
            login(driver, event, s3)
            
            # Check again if the login was successful
            with SessionLocal() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                current_status = task.status if task else None
                if current_status == 'WRONG_PASSWORD':
                    update_task_status(session, task_id, 'FAILED', 'Login failed due to incorrect password')
                    return {
                        "statusCode": 400,
                        "body": "Login failed: Incorrect password"
                    }
            
            # Check if redirected to challenge page
            if urlparse(driver.current_url).netloc == "challenge.spotify.com":
                print("Challenge found", driver.current_url)
                with SessionLocal() as session:
                    solve_captcha(driver, event, session)
                time.sleep(2)
                print("Challenge solved", driver.current_url)
            
            print("Navigating back to profile page. From: ", driver.current_url)
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

        with SessionLocal() as session:
            update_task_status(session, task_id, 'EXTRACTING_USERNAME', 'Attempting to extract username')

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='username-field'] p"))
            )
            username_element = driver.find_element(By.CSS_SELECTOR, "div[data-testid='username-field'] p")
            extracted_username = username_element.text
            print(f"Extracted username: {extracted_username}")
            
            with SessionLocal() as session:
                update_task_status(session, task_id, 'USERNAME_EXTRACTED', f'Username extracted: {extracted_username}')

            client_id = os.getenv('SPOTIFY_CLIENT_ID')
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            token_url = 'https://accounts.spotify.com/api/token'
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            token_response = requests.post(token_url, data=token_data)
            access_token = token_response.json()['access_token']

            user_url = f'https://api.spotify.com/v1/users/{extracted_username}'
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            user_response = requests.get(user_url, headers=headers)
            user_data = user_response.json()
            display_name = user_data.get('display_name', 'Unknown')

            print(f"User display name: {display_name}")

            with SessionLocal() as session:
                update_task_status(session, task_id, 'EXTRACTING_DISPLAY_NAME', f'Display name extracted: {display_name}')

                # Get customer_id from activation key if not a trial
                if not is_trial and activation_key_value:
                    activation_key_obj = session.query(ActivationKey).filter_by(key=activation_key_value).first()
                    if activation_key_obj:
                        customer_id = activation_key_obj.order_line.order.customer_id
                    else:
                        raise Exception("Invalid activation key")
                elif is_trial and not customer_id:
                    raise Exception("Customer ID is required for trial")

                # Upsert the Spotify individual account
                spotify_account = session.query(SpotifyIndividualAccount).filter_by(username=extracted_username).first()
                if spotify_account:
                    spotify_account.display_name = display_name
                    spotify_account.password = password
                    spotify_account.email = email
                    spotify_account.customer_id = customer_id
                else:
                    spotify_account = SpotifyIndividualAccount(
                        username=extracted_username,
                        display_name=display_name,
                        password=password,
                        email=email,
                        is_provided_by_service=False,  # Assuming this is a user-provided account
                        customer_id=customer_id
                    )
                    session.add(spotify_account)
                
                session.commit()
                print(f"Spotify individual account upserted for username: {extracted_username}")

                # Update the task and link to the Spotify individual account
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.spotify_individual_account_id = spotify_account.id
                    session.commit()
                    print(f"Task {task_id} updated with Spotify individual account ID: {spotify_account.id}")

        except Exception as e:
            print(f"Failed to extract user information: {str(e)}")
            saveScreenshotThrowException(driver, s3, "Failed to extract user information. Screenshot saved as ", throw=True)

        with SessionLocal() as session:
            update_task_status(session, task_id, 'UPDATING_PROFILE', 'Updating profile information')
        try:
            select = Select(driver.find_element(By.ID, 'country'))
            value = driver.find_element(By.ID, 'country').is_enabled()
            if not value:
                with SessionLocal() as session:
                    update_task_status(session, task_id, 'ALREADY_PREMIUM', 'User already has premium, cannot join family plan')
                return {
                    "statusCode": 400,
                    "body": "User already has premium, cannot join family plan"
                }
            select.select_by_value('IN')
            selectText = select.first_selected_option.text
            print(f"Country selected: {selectText}")
        except Exception as e:
            print(f"Error checking premium status: {str(e)}")
            saveScreenshotThrowException(driver, s3, "Error checking premium status. Screenshot saved as ", throw=True)
            raise e

        driver.execute_script("window.scrollTo(0, 500)")
        print("Scrolling till the end")

        saveScreenshotThrowException(driver, s3, "Pre save with country selected", throw=False)
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
                    print("Failed to click submit button after 1 attempt")
                    raise e

        with SessionLocal() as session:
            update_task_status(session, task_id, 'JOINING_FAMILY', 'Joining family plan')
        confirm_link = invite_link.replace('/invite/', '/confirm/')
        driver.get(confirm_link)
        print(f'Navigating to confirm page: {confirm_link}')

        # Check if the invite link is expired
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-encore-id='type']"))
            )
            expired_text = driver.find_element(By.CSS_SELECTOR, "h1[data-encore-id='type']").text
            if "expired" in expired_text.lower():
                with SessionLocal() as session:
                    update_task_status(session, task_id, 'LINK_EXPIRED', 'The invite link has expired')
                print("The invite link has expired")
                return {
                    "statusCode": 400,
                    "body": "The invite link has expired"
                }
        except Exception as e:
            print(f"No expiration message found, proceeding with join process: {str(e)}")

        time.sleep(random.uniform(2, 3))

        address_link = invite_link.replace('/join/invite/', '/join/address/')
        driver.get(address_link)
        print(f'Navigating to address page: {address_link}')

        time.sleep(3)
        
        with SessionLocal() as session:
            update_task_status(session, task_id, 'CHECKING_ELIGIBILITY', 'Checking if user is eligible to join family plan')
        print("Checking for 12-month limit")
        #saveScreenshotThrowException(driver, s3, "Pre eligibility check ", throw=False)

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-encore-id='type']"))
            )
            limit_text = driver.find_element(By.CSS_SELECTOR, "p[data-encore-id='type']").text
            if "12 months" in limit_text:
                with SessionLocal() as session:
                    update_task_status(session, task_id, 'LIMIT_12', 'User has been part of a family plan in the last 12 months')
                print("User has been part of a family plan in the last 12 months")
                return {
                    "statusCode": 400,
                    "body": "User has been part of a family plan in the last 12 months"
                }
        except Exception as e:
            print(f"No 12-month limit found, proceeding with address entry: {str(e)}")

        with SessionLocal() as session:
            update_task_status(session, task_id, 'ENTERING_ADDRESS', 'Entering family address')
        print("Proceeding to enter address")
        saveScreenshotThrowException(driver, s3, "Pre address ", throw=False)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'address')))
        address = driver.find_element(By.ID, 'address')
        address.click()
        time.sleep(1)
        address.send_keys(physical_address)
        address.send_keys(u'\ue004')
        address.send_keys(u'\ue007')
        time.sleep(1)
        print("Address entered")
        time.sleep(random.uniform(1, 1.5))
        saveScreenshotThrowException(driver, s3, "Clicked submit. Screenshot saved as ", throw=False)
        with SessionLocal() as session:
            update_task_status(session, task_id, 'CONFIRMING', 'Confirming family plan join')
        confirm = driver.find_element(By.CSS_SELECTOR, "[data-encore-id='buttonPrimary']")
        confirm.click()
        time.sleep(random.uniform(1, 1.5))
        saveScreenshotThrowException(driver, s3, "Clicked confirm. Screenshot saved as ", throw=False)
        print("Clicked confirm | Accepted invite")

        # Retrieve the member's name and ID
        script = """
        async function getMemberInfo() {
            const response = await fetch('https://www.spotify.com/api/family/v1/family/home/');
            const data = await response.json();
            const member = data.members.find(m => m.isLoggedInUser);
            return {
                id: member ? member.id : null,
                name: member ? member.name : null,
                homeId: data.homeId
            };
        }
        return getMemberInfo();
        """
        member_info = driver.execute_script(script)
        
        if member_info['id'] and member_info['name']:
            print(f"Retrieved member info: ID: {member_info['id']}, Name: {member_info['name']}, Home ID: {member_info['homeId']}")
        else:
            print("Failed to retrieve member info")
            raise Exception("Failed to retrieve member info")

        with SessionLocal() as session:
            update_task_status(session, task_id, 'COMPLETED', 'Successfully joined family plan')
            
            # Mark the activation key as redeemed only if it's not a trial
            if not is_trial and activation_key_value:
                activation_key_obj = session.query(ActivationKey).filter(ActivationKey.key == activation_key_value).first()
                if activation_key_obj:
                    activation_key_obj.status = 'REDEEMED'
                    activation_key_obj.used_at = datetime.datetime.now(datetime.timezone.utc)
            
            # Get the family account
            family_account = session.query(SpotifyFamilyAccount).filter_by(id=family_account_id).first()
            if family_account and family_account.status == 'ACTIVE':
                # Find an available spot number
                used_spots = session.query(SpotifyFamilySpotPeriod.spot_number).filter(
                    SpotifyFamilySpotPeriod.spotify_family_account_id == family_account_id,
                    SpotifyFamilySpotPeriod.status.in_(['ACTIVE', 'GRACE_PERIOD'])
                ).all()
                used_spot_numbers = [spot.spot_number for spot in used_spots]
                all_spots = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE']
                available_spot = next((spot for spot in all_spots if spot not in used_spot_numbers), None)

                if is_trial:
                    new_order = ShopOrder(
                        order_date=datetime.datetime.now(datetime.timezone.utc),
                        status='CREATED',
                        total_amount=0,
                        currency='EUR',
                        customer_id=customer_id
                    )
                    session.add(new_order)
                    session.flush()  # This will populate the id field of new_order
                
                if available_spot:
                    # Create a new spot period
                    new_period = SpotifyFamilySpotPeriod(
                        start_date=datetime.datetime.now(datetime.timezone.utc),
                        end_date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365),  # Assuming 1-year period
                        status='ACTIVE',
                        order_id=new_order.id if is_trial else activation_key_obj.order_line.order_id if not is_trial and activation_key_obj and activation_key_obj.order_line else None,
                        customer_id=customer_id,
                        spotify_account_id=spotify_account.id,
                        spot_number=available_spot,
                        spotify_family_account_id=family_account.id,
                        spotify_member_id=member_info['id'] if member_info else None,
                        spotify_member_name=member_info['name'] if member_info else None,
                        is_trial=is_trial,
                        trial_end_date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=TRIAL_DURATION) if is_trial else None,
                        payment_grace_period_end_date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=GRACE_PERIOD) if is_trial else None
                    )
                    session.add(new_period)
                    
                    # Link the family account to the task
                    task = session.query(Task).filter(Task.id == task_id).first()
                    if task:
                        task.spotify_family_accountId = family_account.id

                    # Link the customer to the task
                    if task:
                        task.customer_id = customer_id

                    # Associate the activation key with the new period only if it's not a trial
                    if not is_trial and activation_key_obj:
                        activation_key_obj.spotify_family_spot_period = new_period

                    # Update the number of members in the family account
                    family_account.number_of_members += 1

                    session.commit()

                    # Schedule deletion for trial memberships
                    if is_trial:
                        step_function_arn = 'arn:aws:states:ap-south-1:374320688826:stateMachine:schedule-member-deletion'
                        
                        input_data = {
                            "execute_in_seconds": TRIAL_DURATION,
                            "spotify_member_id": new_period.spotify_member_id,
                            "after_trial": True
                        }
                        
                        try:
                            response = client.start_execution(
                                stateMachineArn=step_function_arn,
                                input=json.dumps(input_data)
                            )
                            print(f"Step Function execution started: {response['executionArn']}")
                        except Exception as sf_error:
                            print(f"Error starting Step Function: {str(sf_error)}")
                            # Note: We're not raising an exception here to avoid rolling back the successful join operation
                else:
                    raise Exception("No available spots in the family plan")
            else:
                raise Exception("Family account not found or not active")

    except Exception as e:
        error_message = str(e)
        print(f"Error occurred: {error_message}")
        saveScreenshotThrowException(driver, s3, f"Error: {error_message}. Screenshot saved as ", throw=True)
        
        with SessionLocal() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            current_status = task.status if task else None
            if current_status not in ['WRONG_PASSWORD', 'CAPTCHA_FAILED', 'ALREADY_PREMIUM', 'LIMIT_12', 'LINK_EXPIRED']:
                update_task_status(session, task_id, 'FAILED', f'Error: {error_message}')
            
            # If an error occurs, revert the activation key status to 'ACTIVE' only if it's not a trial
            if not is_trial and activation_key_value:
                activation_key_obj = session.query(ActivationKey).filter(ActivationKey.key == activation_key_value).first()
                if activation_key_obj and activation_key_obj.status == 'IN_USE':
                    activation_key_obj.status = 'ACTIVE'
                    session.commit()
        
        return {
            "statusCode": 500,
            "body": error_message
        }
            
    finally:
        try:
            driver.get('https://www.spotify.com/en/logout/')
            print("Logging out")  
            time.sleep(0.5)
        except Exception as logout_error:
            print(f"Error during logout: {str(logout_error)}")
        finally:
            session.close()
            driver.quit()

    response = {
        "statusCode": 200,
        "body": "Successfully joined family plan"
    }

    return response