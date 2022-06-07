import flask, logging
import database, digitalocean, loadbalancer, docker
from extensions import database
from models import NodeType

router = flask.Blueprint('expand', __name__)

@router.route('/expand', methods=['POST'])
def post():
    node_id = flask.request.form.get('id')
    node_type = flask.request.form.get('type')