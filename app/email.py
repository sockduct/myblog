from app import mail
from flask import current_app
from flask_mail import Message
from threading import Thread


def send_async_email(app, msg):
    # Flask uses app_context for each thread that uses flask
    # Since mail.send uses flask config data, start new app_context
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body, attachments=None,
               sync=False):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # Initial pass - problem, blocks program until completes:
    # mail.send(msg)
    # Revised version - use a separate thread to send:
    # Note - also need to pass app instance as mail needs to lookup things like
    # mail server
    # Have to use _get_current_object method because current_app is a proxy
    # tied to a specific thread (thread local) and not the actual app instance
    # Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
    #
    # Replace straight Thread based invocation with support for a task queue
    # Add support for sending attachments
    if attachments:
        # attachments is a list, each attachment contains tuple of necessary args
        for attachment in attachments:
            # To include attachments, need 3 args - filename, content type, data
            # The filename doesn't need to be real - this is just what the attachment
            # will be named in the email
            # content type is the MIME type and data is the raw data stream
            msg.attach(*attachment)
    # If using a task queue, running in a separate thread doesn't make sense - already
    # running in a worker outside the app so invoke synchronous delivery:
    if sync:
        mail.send(msg)
    # If running from the app (e.g., password reset) then continue to use separate thread
    else:
        Thread(target=send_async_email,
            args=(current_app._get_current_object(), msg)).start()

