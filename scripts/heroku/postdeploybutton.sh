#!/bin/bash

# Print out details as our script runs
set -x

# Create the necessary database tables
python manage.py migrate

# Install bower components, use the local bower cache if available
bower install --verbose --config.storage.packages=vendor/bower/packages --config.storage.registry=vendor/bower/registry --config.tmp=vendor/bower/tmp --config.interactive=false

# Run grunt commands that compile frontend code
grunt

# Use our modified `fasts3collectstatic` collectstatic command to push content to s3
python manage.py fasts3collectstatic --noinput
