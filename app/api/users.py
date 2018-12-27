from flask import jsonify, request, url_for, g, abort
from app import db
from app.models import User
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request


# Note - even though all these routes start with '/api' this isn't shown here
#        as this is handled by blueprint registration
# Don't have to list GET as a method - that's the default; however, for APIs
# the instructor prefers to be explicit
@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    return jsonify(User.query.get_or_404(id).to_dict())


# Since this is a collection of users, must handle pagination
@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    # Extract page and per_page from query string
    page = request.args.get('page', 1, type=int)
    # Limit per_page range from 10 to 100 - reasonable range to prevent
    # overtaxing server
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(User.query, page, per_page, 'api.get_users')
    return jsonify(data)


# The next two functions are similar to the above but add a keyword argument
# to the invocation of to_collection_dict
@bp.route('/users/<int:id>/followers', methods=['GET'])
@token_auth.login_required
def get_followers(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(user.followers, page, per_page,
                                   'api.get_followers', id=id)
    return jsonify(data)


@bp.route('/users/<int:id>/followed', methods=['GET'])
@token_auth.login_required
def get_followed(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(user.followed, page, per_page,
                                   'api.get_followed', id=id)
    return jsonify(data)


# No authentication required to allow creation of new users
@bp.route('/users', methods=['POST'])
def create_user():
    # Extract JSON payload from request using Flask helper
    # If its missing (None), use {}
    data = request.get_json() or {}
    if 'username' not in data or 'email' not in data or 'password' not in data:
        # Where missing data, invoke bad_request function
        return bad_request('must include username, email and password fields')
    if User.query.filter_by(username=data['username']).first():
        return bad_request('please use a different username')
    if User.query.filter_by(email=data['email']).first():
        return bad_request('please use a different email address')
    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()
    response = jsonify(user.to_dict())
    # Normal status code for POST request which creates a resource vs. default
    # of 200
    response.status_code = 201
    # HTTP requires a Location header for a 201 status code
    response.headers['Location'] = url_for('api.get_user', id=user.id)
    return response


@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_user(id):
    if g.current_user.id != id:
        # 403 = Forbidden or authorization failed
        # Only owning user can change his/her username
        abort(403)
    user = User.query.get_or_404(id)
    data = request.get_json() or {}
    # Check if field present, if present has it changed, if yes then is it
    # unique
    if 'username' in data and data['username'] != user.username and \
            User.query.filter_by(username=data['username']).first():
        return bad_request('please use a different username')
    if 'email' in data and data['email'] != user.email and \
            User.query.filter_by(email=data['email']).first():
        return bad_request('please use a different email address')
    # Not a new user, password changes not allowed/supported here
    user.from_dict(data, new_user=False)
    db.session.commit()
    return jsonify(user.to_dict())

