import flask

router = flask.Blueprint('index', __name__, template_folder='templates')

@router.route('/', methods=['GET'])
def get():
    return flask.render_template('index.html')