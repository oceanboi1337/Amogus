from extensions import database
from decorators.auth import auth
import flask

router = flask.Blueprint('login', __name__, template_folder='templates')

@router.route('/login', methods=['GET'])
def get():
    return flask.render_template('login.html')

@router.route('/login', methods=['POST'])
def post():
    email = flask.request.form.get('email')
    password = flask.request.form.get('password')

    if email == None or password == None:
        return flask.render_template('login.html', code=401)

    if uid := database.login(email, password):
        flask.session['uid'] = uid
        return flask.redirect('/webapp')
    
    return flask.render_template('login.html'), 401