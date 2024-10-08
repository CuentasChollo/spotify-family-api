import json
import uuid
import boto3
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task, SpotifyFamilyAccount, ActivationKey, SpotifyFamilySpotPeriod, Customer
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

lambda_client = boto3.client('lambda')

"""
Inputs:
- family_account_id: string 
- activation_key_value: string
- email: string
- password: string
- is_trial: boolean (optional, defaults to False)
- customer_id: string (optional, defaults to None) //This value is mandatory if its trial
"""
def init_join_family(event, context):
    try:
        session = Session()

        family_account_id = event.get('family_account_id')
        activation_key_value = event.get('activation_key_value')
        email = event.get('email')
        password = event.get('password')
        is_trial = event.get('is_trial', False)  # Default to False if not provided
        customer_id = event.get('customer_id', None)
        # Check if required fields are not empty
        if not email or not password:
            return {
                'error': 'Email and password are required.'
            }
        
        # Check if family_account_id is a number
        if family_account_id and not isinstance(family_account_id, (int, float)):
            return {
                'error': 'family_account_id must be a number.'
            }
        
        # Check if it's a trial and if a valid customer_id is provided
        if is_trial:
            if not customer_id:
                return {
                    'error': 'Customer ID is required for trial.'
                }
            customer = session.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {
                    'error': 'Invalid customer ID.'
                }
        
        # Check if the activation key is valid and of the correct type only if it's not a trial
        if activation_key_value and not is_trial:
            key = session.query(ActivationKey).filter(
                ActivationKey.key == activation_key_value,
                ActivationKey.status == 'ACTIVE',
                ActivationKey.activation_type == 'FAMILY_SPOT'
            ).first()
            if not key:
                return {
                    'error': 'Invalid or incorrect type of activation key.'
                }
            
            # Set the activation key status to 'IN_USE'
            key.status = 'IN_USE'
            session.commit()

        if family_account_id:
            family_account = session.query(SpotifyFamilyAccount).filter(
                SpotifyFamilyAccount.id == family_account_id
            ).first()
            if not family_account:
                return {
                    'error': 'No family account found with the provided ID.'
                }
        else:
            family_account = session.query(SpotifyFamilyAccount).filter(
                SpotifyFamilyAccount.status == 'ACTIVE'
            ).first()
            if not family_account:
                return {
                    'error': 'No active family account found.'
                }

        # Check for available spots
        current_spots = session.query(SpotifyFamilySpotPeriod).filter(
            SpotifyFamilySpotPeriod.spotify_family_account_id == family_account.id,
            SpotifyFamilySpotPeriod.status.in_(['ACTIVE', 'GRACE_PERIOD'])
        ).count()

        if current_spots >= 5:  # Assuming a maximum of 5 spots per family account
            return {
                'error': 'No available spots in the selected family account.'
            }

        # If we've made it here, we have a valid family account and activation key (if provided and not a trial)
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        new_task = Task(id=task_id, type='JOIN_FAMILY', status='INITIATED', created_at=created_at, updated_at=created_at)
        session.add(new_task)
        session.commit()

        invite_link = family_account.invite_link
        physical_address = family_account.physical_address

        if not invite_link.endswith('/'):
            invite_link += '/'

        event.update({
            'invite_link': invite_link,
            'physical_address': physical_address,
            'task_id': task_id,
            'family_account_id': family_account.id,
            'activation_key_value': activation_key_value,
            'email': email,
            'password': password,
            'is_trial': is_trial,
            'customer_id': customer_id
        })

        lambda_client.invoke(
            FunctionName="join-family",
            InvocationType='Event',
            Payload=json.dumps(event)
        )
    
        return {
            'task_id': task_id
        }

    except Exception as e:
        print(f"Error in init_join_family: {str(e)}")
        # If an error occurs, revert the activation key status to 'ACTIVE' only if it's not a trial
        if activation_key_value and not is_trial:
            key = session.query(ActivationKey).filter(
                ActivationKey.key == activation_key_value
            ).first()
            if key and key.status == 'IN_USE':
                key.status = 'ACTIVE'
                session.commit()
        return {
            'error': 'Failed to initialize task'
        }
    finally:
        session.close()