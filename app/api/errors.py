from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES


# Clients don't want/expect HTML error page so must handle errors differently for
# API clients
def error_response(status_code, message=None):
    # HTTP_STATUS_CODES is a dictionary with the status codes as the keys and
    # a short description of each one for the value
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    # jsonify returns Flask Response object with default status code of 200
    # wraps dumps and sets media type correctly to application/json
    # Also a little more versatile than dumps
    response = jsonify(payload)
    # Reset status_code to correct passed in value (vs. default of 200)
    response.status_code = status_code
    return response


# Most common API error - client sends request thats incomplete/invalid
# This is a convenience function wrapping error_response
def bad_request(message):
    return error_response(400, message)

