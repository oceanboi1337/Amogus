import flask, bcrypt
from extensions import database

router = flask.Blueprint('login', __name__, template_folder='templates')

@router.route('/register', methods=['GET'])
def get():
    return flask.render_template('register.html')

@router.route('/register', methods=['POST'])
def post():
    email = flask.request.form.get('email')
    password = flask.request.form.get('password')
    
    if email == None or password == None:
        return flask.render_template('register.html'), 400

    salt = bcrypt.gensalt(12)
    hash = bcrypt.hashpw(password.encode('utf-8'), salt=salt)

    if uid := database.register(email, hash):
        flask.session['uid'] = uid
        return flask.redirect('/webapp')

    return flask.render_template('register.html'), 500