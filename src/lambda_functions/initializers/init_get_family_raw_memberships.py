import json
import uuid
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

lambda_client = boto3.client('lambda')

def init_get_family_raw_memberships(event, context):
    # Check if email and password are provided in the event
    if 'email' not in event or 'password' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Email and password are required'}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    session = Session()
    try:
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        new_task = Task(id=task_id, type='GET_FAMILY_RAW_MEMBERSHIPS', status='INITIATED', created_at=created_at, updated_at=created_at)
        session.add(new_task)
        session.commit()

        # Add task_id to the event
        event['task_id'] = task_id

        # Invoke the main function asynchronously
        lambda_client.invoke(
            FunctionName="get-family-raw-memberships",
            InvocationType='Event',
            Payload=json.dumps(event)
        )

        # Return a cleaner response
        return {
            'task_id': task_id
        }
    except ClientError as e:
        print(f"Error invoking Lambda function: {e}")
        return {
            'error': 'Failed to start task'
        }
    finally:
        session.close()