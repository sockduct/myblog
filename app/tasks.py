import json
import sys
import time
from flask import render_template
from rq import get_current_job
from app import create_app, db
from app.models import User, Post, Task
from app.email import send_email


# Create an app instance - this module will run in a separate process and
# thus won't have access to current_app; instead need to create an app
# instance to allow access to flask_sqlalchemy and flask_mail used by app
app = create_app()
# Need an app context to allow access to current_app
# Flask extensions like SQLAlchemy need this to work
app.app_context().push()


# Manage task progress tracking
def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        # Provide a way to keep use apprised of task progress asynchronously
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def export_posts(user_id):
    # Since running under rq, need to handle exceptions and perform cleanup
    # Otherwise errors would go unnoticed (no one is going to sit and watch
    # the console for errors!)
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)
        data = []
        # Use i and total_posts to track progress
        i = 0
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            # .isoformat() uses the ISO 8601 datetime format
            # 'Z' represents UTC timezone
            data.append({'body': post.body,
                         'timestamp': post.timestamp.isoformat() + 'Z'})
            # Slow down export to test task progress functionality
            time.sleep(5)
            i += 1
            _set_task_progress(100 * i // total_posts)

        send_email('[Myblog] Your blog posts',
                sender=app.config['ADMINS'][0], recipients=[user.email],
                text_body=render_template('email/export_posts.txt', user=user),
                html_body=render_template('email/export_posts.html',
                                          user=user),
                attachments=[('posts.json', 'application/json',
                              json.dumps({'posts': data}, indent=4))],
                sync=True)
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

