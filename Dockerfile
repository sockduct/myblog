# Each line is a command within Dockerfile
# Base container image - Python 3.6 on Alpine Linux
# Alpine often used instead of Ubuntu because of small size
FROM python:3.6-alpine

# Execute command within container, like running from root shell
RUN adduser -D myblog

# Set default directory
WORKDIR /home/myblog

# Transfer files from local machine to container
# Source file is relative to where Dockerfile located
# Destination path can be absolute or relative to WORKDIR
COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install --upgrade pip
RUN venv/bin/pip install -r requirements.txt
# Since this isn't listed in requirements, add explicitly
# Could also have added to requirements file
RUN venv/bin/pip install gunicorn
# Temporarily install compiler to build mysql dependencies
RUN apk add --no-cache --virtual .pynacl_deps build-base python3-dev libffi-dev libressl-dev musl-dev
RUN venv/bin/pip install pymysql
# Remove compiler
RUN apk del .pynacl_deps

COPY app app
COPY migrations migrations
COPY myblog.py config.py boot.sh ./
# Make sure its executable, important if coming from Windows system
RUN chmod +x boot.sh

# Set environment variable within container
ENV FLASK_APP myblog.py

# Default user for all commands is root, so switch everything to be owned by myblog
RUN chown -R myblog:myblog ./
# Change default user to myblog for subsequent commands and when container is started
USER myblog

# Port this container will use for its server
EXPOSE 5000
# When to execute when container starts
ENTRYPOINT ["./boot.sh"]
# Note - Run commands happen when you build the Docker image
# The Entrypoint program executes when you start the container

