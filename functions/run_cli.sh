#!/bin/bash
cd functions
# Check if the image already exists
if [[ "$(docker images -q audible-opds-firebase 2> /dev/null)" == "" ]]; then
  echo "Building Docker image..."
  docker build -t audible-opds-firebase .
else
  echo "Using existing Docker image."
fi

# Run the container and execute main.py
docker run -it -v "$(pwd)":/app audible-opds-firebase python auth.py