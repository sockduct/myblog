from app import app, mail
from flask import render_template
from flask_babel import _
from flask_mail import Message
from threading import Thread


def send_async_email(app, msg):
    # Flask uses app_context for each thread that uses flask
    # Since mail.send uses flask config data, start new app_context
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # Initial pass - problem, blocks program until completes:
    # mail.send(msg)
    # Revised version - use a separate thread to send:
    # Note - also need to pass app instance as mail needs to lookup things like
    # mail server
    Thread(target=send_async_email, args=(app, msg)).start()


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(_('[Myblog] Reset Your Password'),
               sender=app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt', user=user, token=token),
               html_body=render_template('email/reset_password.html', user=user, token=token))

