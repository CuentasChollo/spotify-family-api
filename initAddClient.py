import json
import boto3
import uuid
import requests

dynamodb = boto3.resource('dynamodb')
lamda = boto3.client('lambda')
tasks_table = dynamodb.Table('tasks')
familly_acc_table = dynamodb.Table('familly_accounts')

def init_add_client(event, context):
    task_id = str(uuid.uuid4())
    tasks_table.put_item(Item={'task_id': task_id, 'status_string': 'IN_PROGRESS'})


    #Search in familly_accounts table for a account that less than 5 'people_in', get the 'invite_code' and the 'address'
    response = familly_acc_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('people_in').lt(5)
    )

    accounts = response.get('Items', [])
    selected_account = accounts[0] if accounts else None

    if not selected_account:
        # Handle the case where no account meets the criteria
        return {
            'error': 'No available family account found with less than 5 people.'
        }

    invite_code = selected_account['invite_code']
    address = selected_account['address']

    #Call addClient long function | https://eyjcw5rsrt3hv6lbpecscuiyoa0xkqda.lambda-url.ap-south-1.on.aws/
    #Passing the event adding to it the field invite_code and address, task_id
    function_URL = "https://eyjcw5rsrt3hv6lbpecscuiyoa0xkqda.lambda-url.ap-south-1.on.aws/"
    event['invite_code'] = invite_code
    event['address'] = address
    event['task_id'] = task_id

    lamda.invoke(
        FunctionName="add-family-client",
        InvocationType='Event',
        Payload=json.dumps(event)
    )
    
    return task_id	
