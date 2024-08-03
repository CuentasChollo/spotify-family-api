import json
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
lamda = boto3.client('lambda')
tasks_table = dynamodb.Table('tasks')
familly_acc_table = dynamodb.Table('familly_accounts')

def init_add_client(event, context):
    task_id = str(uuid.uuid4())
    tasks_table.put_item(Item={'task_id': task_id, 'status_string': 'INITIALIZING'})

    invite_link = None
    physicalAddress = None

    if 'inviteLink' in event and 'physicalAddress' in event:
        invite_link = event['inviteLink']
        physicalAddress = event['physicalAddress']
        
        # Ensure the invite link ends with a slash
        if not invite_link.endswith('/'):
            invite_link += '/'
    
    if not invite_link or not physicalAddress:
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

        invite_link = selected_account['invite_link']
        physicalAddress = selected_account['address']

    event['inviteLink'] = invite_link
    event['physicalAddress'] = physicalAddress
    event['task_id'] = task_id

    lamda.invoke(
        FunctionName="add-family-client",
        InvocationType='Event',
        Payload=json.dumps(event)
    )
    
    return {
    'statusCode': 200,
    'body': json.dumps({'task_id': task_id}),
    'headers': {
        'Content-Type': 'application/json'
        }
    }