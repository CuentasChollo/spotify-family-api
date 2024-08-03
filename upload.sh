aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 374320688826.dkr.ecr.ap-south-1.amazonaws.com
docker build -t selenium-lambda . --platform=linux/amd64
docker tag selenium-lambda:latest 374320688826.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest
docker push 374320688826.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest

# Execute ecr cleanup script
./cleanup.sh
