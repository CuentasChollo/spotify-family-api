aws ecr get-login-password --region your-aws-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-aws-region.amazonaws.com
docker build -t your-image-name . --platform=linux/amd64
docker tag your-image-name:latest your-account-id.dkr.ecr.your-aws-region.amazonaws.com/your-repository-name:latest
docker push your-account-id.dkr.ecr.your-aws-region.amazonaws.com/your-repository-name:latest

# Execute ecr cleanup script
./scripts/cleanup.sh
