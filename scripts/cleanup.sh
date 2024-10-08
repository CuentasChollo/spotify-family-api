#!/bin/bash

# Set your AWS region and repository URI
AWS_REGION="your-aws-region"
REPOSITORY_URI="your-account-id.dkr.ecr.your-aws-region.amazonaws.com/your-repository-name"

# Extract repository name from URI
REPOSITORY_NAME=$(echo $REPOSITORY_URI | awk -F'/' '{print $2}')

# List all images, sort by date, and keep only the image digests
IMAGE_DIGESTS=$(aws ecr list-images --repository-name "$REPOSITORY_NAME" --region "$AWS_REGION" --query 'imageDetails[*].imageDigest' --output text)

# Check if IMAGE_DIGESTS is empty
if [ -z "$IMAGE_DIGESTS" ]; then
    echo "No images found in the repository."
    exit 0
fi

# Convert the image digests into an array
IFS=' ' read -ra DIGEST_ARRAY <<< "$IMAGE_DIGESTS"

# Calculate the number of images to delete
TOTAL_IMAGES=${#DIGEST_ARRAY[@]}
TO_DELETE=$((TOTAL_IMAGES - 3))

# Check if we need to delete any images
if [ $TO_DELETE -gt 0 ]; then
    echo "Deleting $TO_DELETE images..."
    
    # Prepare the JSON for the batch delete command
    JSON="{ \"imageIds\": ["
    for i in "${DIGEST_ARRAY[@]:0:$TO_DELETE}"; do
        JSON+="{\"imageDigest\":\"$i\"},"
    done
    JSON="${JSON%,}]}"

    # Delete the images
    aws ecr batch-delete-image --repository-name "$REPOSITORY_NAME" --region "$AWS_REGION" --image-ids "$JSON"
    
    echo "Deleted $TO_DELETE images. Keeping the last 3 images."
else
    echo "There are $TOTAL_IMAGES images. No need to delete any."
fi