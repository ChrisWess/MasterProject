from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort, render_template, redirect, url_for, session
from flask_login import login_required
from pymongo.errors import OperationFailure

from app import application, login_manager
from app.db.daos.user_dao import UserDAO


@application.route('/user/create', methods=['POST'])
def create_user():
    try:
        args = request.json
        name = args["name"] if 'name' in args else None
        if "email" not in args or "password" not in args:
            err_msg = 'Your request body must contain at least the key-value pairs with keys "email" and "password"!'
            application.logger.error(err_msg)
            abort(400, err_msg)
        response = UserDAO().add(name, args["email"], args["password"], generate_response=True)
        application.logger.info("User inserted: " + response['result'])
        return response
    except OperationFailure as e:
        application.logger.error(str(e))
        abort(500)
    except ValueError as e:
        application.logger.error(str(e))
        abort(400, e)


@application.route('/register', methods=['GET', 'POST'])
@application.route('/user/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        try:
            args = request.form
            name = args["username"] if 'username' in args else None
            response = UserDAO().add(name, args["email"], args["password"])
            application.logger.info("User registered: " + response['result']['_id'])
            return render_template('login.html', email=args["email"])
        except OperationFailure as e:
            application.logger.error(str(e))
            return render_template('register.html', error="Server error occurred while trying to register user")
        except ValueError as e:
            application.logger.error(str(e))
            return render_template('register.html', error=str(e))
    return render_template('register.html')


@login_manager.unauthorized_handler
def unauthorized_callback():
    # In unauthorized_handler we have a callback URL
    # In call back url we can specify where we want to redirect the user
    # TODO: maybe save in session timestamp of when login happened and if login was a long time ago,
    #  then validate that this user still exists in DB.
    # if request.method == 'GET':
    #    return login()
    # else:
    return {"result": "Unauthorized", "status": 401}


def handle_login_error(err_msg):
    application.logger.error(err_msg)
    email = request.form.get('email', default=None)
    redirect_to = request.args.get('next', default=None)
    context = {"error": err_msg}
    if email:
        context['email'] = email
    if redirect_to:
        context['redirect_to'] = f"?next={redirect_to}"
    return render_template('login.html', **context)


@application.route('/login', methods=['GET', 'POST'])
def login():
    if UserDAO.is_logged_in_in_session() and (not session['userid'] or
                                              UserDAO().find_by_id(ObjectId(session['userid'])) is None):
        UserDAO.logout_user()
        redirect_to = f"?next={request.path}"
        return render_template('login.html', redirect_to=redirect_to)
    if request.method == 'POST':
        try:
            email = request.form['email']
            usr_entered = request.form['password']

            UserDAO().validate_login(email, usr_entered)
            redirect_to = request.args.get('next', default=None)
            if redirect_to:
                return redirect(redirect_to)
            else:
                return redirect(url_for("index"))
        except OperationFailure:
            return handle_login_error("Server error occurred while validating login")
        except ValueError as e:
            return handle_login_error(str(e))
    elif request.endpoint != 'login':
        redirect_to = f"?next={request.path}"
        return render_template('login.html', redirect_to=redirect_to)
    elif request.args and 'next' in request.args:
        redirect_to = f"?next={request.args['next']}"
        return render_template('login.html', redirect_to=redirect_to)
    else:
        return render_template('login.html')


@application.route('/logout', methods=['GET', 'POST'])
def logout():
    if UserDAO.is_logged_in_in_session():
        UserDAO.logout_user()
        return redirect(url_for('index'))
    else:
        return {"result": "Logout unsuccessful! Not logged in.", "status": 401}


@application.route('/user', methods=['GET'])
def find_users():
    return UserDAO().find_all(projection=request.args, generate_response=True)


def get_user_by_id(user_id):
    try:
        user = UserDAO().find_by_id(ObjectId(user_id), projection=request.args, generate_response=True)
        if user is None:
            # TODO: handle 404s in frontend (or maybe better return an JSON response with {"response": 404})
            # TODO: throw 404s in other routes (docs, projects), too:
            #  https://flask.palletsprojects.com/en/2.3.x/quickstart/#about-responses
            err_msg = "No user with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return user
    except InvalidId:
        err_msg = "The entity ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)  # TODO: this should be prevented as far as possible in frontend by field validators


@application.route('/user/current', methods=['GET'])
@login_required
def find_current_user():
    user_id = session.get("userid", default=None)
    if user_id is None:
        err_msg = "Logged in user could not be found!"
        application.logger.error(err_msg)
        abort(400, err_msg)
    return get_user_by_id(user_id)


@application.route('/user/demo', methods=['GET'])
def find_demo_user():
    # FIXME: this is a workaround for development (instead of /user/current), because the React dev
    #  server does not send the session cookie that is necessary on @login_required endpoints
    return UserDAO().find_by_email('demo@mail.com', generate_response=True)


@application.route('/user/<user_id>', methods=['GET'])
def find_user_by_id(user_id=None):
    return get_user_by_id(user_id)


@application.route('/user/byEmail/<email>', methods=['GET'])
def find_user_by_email(email):
    user = UserDAO().find_by_email(email, projection=request.args, generate_response=True)
    if user is None:
        # TODO: return custom JSON body responses with a 404
        err_msg = f"No user with email {email} could be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        return user


@application.route('/user/<user_id>', methods=['DELETE'])
def delete_user_by_id(user_id):
    # TODO: log out deleted user, if logged in
    try:
        response = UserDAO().delete_by_id(ObjectId(user_id), generate_response=True)
        application.logger.info(f"User with ID {user_id} has been deleted")
        return response
    except InvalidId:
        err_msg = "The entity ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/user/byEmail/<email>', methods=['DELETE'])
def delete_user_by_email(email):
    # TODO: log out deleted user, if logged in
    response = UserDAO().delete_by_email(email, generate_response=True)
    application.logger.info(f"User with E-mail {email} has been deleted")
    return response


@application.errorhandler(401)
def do_login_first():
    """Display login page when user is not authorised."""
    return login()
