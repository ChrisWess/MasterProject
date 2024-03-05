from flask import redirect, session, url_for

from app import application, config


@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
def index():
    if session.get("logged_in", default=False):
        return redirect(config.WORKSPACE_URL, code=302)
    else:
        return redirect(url_for("login"))
