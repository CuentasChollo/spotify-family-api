# Selenium Lambda Project 🐍

This project sets up a Selenium environment in an AWS Lambda function, using a custom Docker image.

## Prerequisites

- Docker
- AWS CLI configured with appropriate permissions
- An AWS ECR repository named "selenium" in the ap-south-1 region

## Setup

1. Clone this repository to your local machine.

2. Create a `.env` file in the project root with the following content:

```
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

Replace `your_access_key_id`, `your_secret_access_key` with your actual AWS credentials.

3. Build the Docker image by running the following command:

```
docker build -t selenium .
```

4. Push the Docker image to your ECR repository:

```
docker tag selenium:latest <account_id>.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.ap-south-1.amazonaws.com
docker push <account_id>.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest
```

5. Update the `lambda_function.py` file with the correct ECR image URL and environment variables.

6. Deploy the Lambda function using the AWS CLI:

```
aws lambda create-function --function-name selenium-lambda --runtime python3.8 --role <lambda_execution_role_arn> --handler lambda_function.lambda_handler --environment Variables={"AWS_ACCESS_KEY_ID":"${AWS_ACCESS_KEY_ID}","AWS_SECRET_ACCESS_KEY":"${AWS_SECRET_ACCESS_KEY}","AWS_API_KEY":"${AWS_API_KEY}"} --image-uri <account_id>.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest --timeout 300
```

7. Test the Lambda function by invoking it:

```
aws lambda invoke --function-name selenium-lambda --payload '{}' response.json
```

8. Verify the output in the `response.json` file.

Note: Make sure to replace `<account_id>` with your actual AWS account ID, and `<lambda_execution_role_arn>` with the ARN of the IAM role that will be used to execute the Lambda function.



## Command to generate the model
sqlacodegen postgresql://postgres.ergwosoutrzabjxuvkvg:[PASS]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres > models.py
