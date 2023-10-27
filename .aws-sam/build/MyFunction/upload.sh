docker build -t selenium-lambda . --platform=linux/amd64
docker tag selenium-lambda:latest 374320688826.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest
docker push 374320688826.dkr.ecr.ap-south-1.amazonaws.com/selenium:latest


