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
spotify_member_id
after_trial: Boolean? //Default false
"""
def init_delete_member(event, context):
    spotify_member_id = event.get('spotify_member_id')
    after_trial = event.get('after_trial', False)
    
    if not spotify_member_id:
        return {
            'error': 'spotify_member_id is required.'
        }

    session = Session()
    try:
        # Find the SpotifyFamilySpotPeriod associated with the spotify_member_id
        spot_period = session.query(SpotifyFamilySpotPeriod).filter(
            SpotifyFamilySpotPeriod.spotify_member_id == spotify_member_id
        ).first()

        if not spot_period:
            return {
                'error': 'No SpotifyFamilySpotPeriod found for the given spotify_member_id.'
            }

        # Get the associated SpotifyFamilyAccount
        family_account = session.query(SpotifyFamilyAccount).filter(
            SpotifyFamilyAccount.id == spot_period.spotify_family_account_id
        ).first()

        if not family_account:
            return {
                'error': 'No SpotifyFamilyAccount found for the given spotify_member_id.'
            }

        family_email = family_account.email
        family_password = family_account.password

        # Create a new task
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        new_task = Task(id=task_id, type='DELETE_MEMBER', status='INITIATED', created_at=created_at, updated_at=created_at)
        session.add(new_task)
        session.commit()

        event.update({
            'task_id': task_id,
            'spotify_member_id': spotify_member_id,
            'email': family_email,
            'password': family_password,
            'after_trial': after_trial
        })

        lambda_client.invoke(
            FunctionName="delete-member",
            InvocationType='Event',
            Payload=json.dumps(event)
        )

        return {
            'task_id': task_id
        }

    except Exception as e:
        print(f"Error in init_delete_member: {str(e)}")
        return {
            'error': 'Failed to initialize delete member task'
        }
    finally:
        session.close()