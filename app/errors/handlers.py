from app import db
from app.api.errors import error_response as api_error_response
from app.errors import bp
from flask import render_template, request


# Allow client to do content negotiation to ask for JSON response vs. HTML
def wants_json_response():
    ### Debugging
    '''
    print(f'request.accept_mimetypes:  {request.accept_mimetypes}')
    print(f'request.accept_mimetypes[application/json]:  '
          f'{request.accept_mimetypes["application/json"]}')
    print(f'request.accept_mimetypes[text/html]:  '
          f'{request.accept_mimetypes["text/html"]}')
    '''
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']


@bp.app_errorhandler(403)
def forbidden_error(error):
    if wants_json_response():
        return api_error_response(403)
    return render_template('errors/403.html'), 403


@bp.app_errorhandler(404)
def not_found_error(error):
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if wants_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500

