import json
import boto3
import uuid
import requests
from urllib.parse import urlparse, parse_qs

dynamodb = boto3.resource('dynamodb')
lamda = boto3.client('lambda')
tasks_table = dynamodb.Table('tasks')
familly_acc_table = dynamodb.Table('familly_accounts')

def init_add_client(event, context):
    task_id = str(uuid.uuid4())
    tasks_table.put_item(Item={'task_id': task_id, 'status_string': 'INITIALIZING'})

    invite_code = None
    physicalAddress = None

    if 'inviteLink' in event and 'physicalAddress' in event:
        # Parse invite_code from the inviteLink
        parsed_url = urlparse(event['inviteLink'])
        path_segments = parsed_url.path.split('/')
        invite_code = path_segments[-1] if path_segments else None
        physicalAddress = event['physicalAddress']
    
    if not invite_code or not physicalAddress:
        # Search in familly_accounts table for an account with less than 5 'people_in'
        response = familly_acc_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('people_in').lt(5)
        )

        accounts = response.get('Items', [])
        selected_account = accounts[0] if accounts else None

        if not selected_account:
            return {
                'error': 'No available family account found with less than 5 people.'
            }

        invite_code = selected_account['invite_code']
        physicalAddress = selected_account['address']

    event['invite_code'] = invite_code
    event['physicalAddress'] = physicalAddress
    event['task_id'] = task_id

    lamda.invoke(
        FunctionName="add-family-client",
        InvocationType='Event',
        Payload=json.dumps(event)
    )
    
    return task_id
