import json
import uuid
import boto3
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task, SpotifyFamilyAccount, EmailUpdateTaskPayload
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
- new_email: string
"""
def init_change_email(event, context):
    try:
        session = Session()

        family_account_id = event.get('family_account_id')
        new_email = event.get('new_email')

        # Check if required fields are not empty
        if not family_account_id or not new_email:
            return {
                'error': 'Family account ID and new email are required.'
            }
        
        # Check if family_account_id is a number
        if not isinstance(family_account_id, (int, float)):
            return {
                'error': 'family_account_id must be a number.'
            }

        family_account = session.query(SpotifyFamilyAccount).filter(
            SpotifyFamilyAccount.id == family_account_id
        ).first()
        if not family_account:
            return {
                'error': 'No family account found with the provided ID.'
            }

        # Create a new task
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        new_task = Task(id=task_id, type='EMAIL_UPDATE', status='INITIATED', created_at=created_at, updated_at=created_at, spotify_family_accountId=family_account.id)
        session.add(new_task)

        # Create EmailUpdateTaskPayload
        email_update_payload = EmailUpdateTaskPayload(
            id=str(uuid.uuid4()),
            task_id=task_id,
            old_email=family_account.email,
            new_email=new_email
        )
        session.add(email_update_payload)
        
        session.commit()

        event.update({
            'task_id': task_id,
            'email': family_account.email,
            'password': family_account.password,
            'new_email': new_email
        })

        lambda_client.invoke(
            FunctionName="change-email",
            InvocationType='Event',
            Payload=json.dumps(event)
        )
    
        return {
            'task_id': task_id
        }

    except Exception as e:
        print(f"Error in init_change_email: {str(e)}")
        return {
            'error': 'Failed to initialize task'
        }
    finally:
        session.close()
