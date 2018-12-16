#!/bin/sh
#
# This script is used to boot a Docker container
#
source venv/bin/activate
# When we use mysql in a separate container, it may take a little bit before
# the flask db upgrade command will work - the loop ensures this
# This is because the boot order may vary and thus the mysql database may
# not be immediately available
# If we stick with SQLite, this isn't necessary
while true; do
    flask db upgrade
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo Deploy command failed, retrying in 5 seconds...
    sleep 5
done
flask translate compile

# Replace process running script with gunicorn
# Important because Docker associates life of container with this startup process
# When process ends, Docker terminates container!
exec gunicorn -b :5000 --access-logfile - --error-logfile - myblog:app
# Note - Docker saves stdout and stderr as logs, so we configure gunicorn
# with --access-logfile and --error-logfile followed by a "-" which signifies
# send the log to stdout

