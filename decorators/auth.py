from functools import wraps
import flask

def auth(f):
    @wraps(f)
    def function(*args, **kwargs):
        if flask.session.get('uid') == None:
            return flask.redirect(flask.url_for('login.get', next=flask.request.url))
        return f(*args, **kwargs)
    return function