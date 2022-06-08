from venv import create
from extensions import database, digitalocean, docker, loadbalancer
from digitalocean import CloudImage, CloudRegion, CloudSize
import flask, magic
import zipfile, io, logging
from loadbalancer import Loadbalancer
from models import NodeType
from decorators.auth import auth

router = flask.Blueprint('webapp', __name__, template_folder='templates')

@router.route('/webapp', methods=['GET'])
@auth
def get():
    return flask.render_template('webapp.html', uid=flask.session.get('uid'))

@router.route('/webapp', methods=['POST'])
@auth
def post():
    uid = flask.session.get('uid')
    domain = flask.request.form.get('domain')
    file = flask.request.files.get('file')

    if file == None or domain == None:
        return flask.render_template('webapp.html'), 400

    file_bytes = file.stream.read()
    allowed_types = ['application/zip']

    # Check if uploaded file is in the list of allowed file types.
    if magic.from_buffer(file_bytes, mime=True) not in allowed_types:
        return flask.render_template('webapp.html'), 403

    # Creates a memory mapped file from the file buffer.
    buffer = io.BytesIO(file_bytes)
    with zipfile.ZipFile(buffer, 'r', zipfile.ZIP_DEFLATED, False) as f:
        f.extractall(f'/var/www/{domain}')

    # Add the domain of the app linked with the UID to the database.
    if not database.add_webapp(uid, domain):
        return flask.render_template('webapp.html'), 409

    # Check if there is any available droplets in the database.
    # If there also is no droplet being created at the moment, create a new droplet
    droplets = database.droplets()

    if len(droplets) <= 0 and len(database.droplets(active=False)) <= 0:
        if droplet := digitalocean.create_droplet('app-node-1', CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
            database.new_droplet(droplet.id, droplet.hostname)
            loadbalancer.register_droplet(droplet)
            return flask.render_template('webapp.html', message='Your WebApp will be deployed shortly')
        return flask.render_template('webapp.html', message='Failed to deploy your WebApp, try again later')

    # Iterate every droplet in the database to try create a container on it.
    for db_droplet in droplets:

        droplet = digitalocean.fetch_droplet(db_droplet.get('id'))
        if droplet == None:
            continue

        if droplet.available_slots() > 0 and (container := docker.create(domain, droplet)):

                database.new_container(domain, container.id, droplet.id)
                database.activate_webapp(domain)

                loadbalancer.add(domain, container)
                loadbalancer.add(domain, droplet)

                return flask.render_template('webapp.html', message='Your WebApp has been deployed')

    # Create a new droplet since there was none with any available slots.
    hostname = f'app-node-{len(droplets)+1}'
    if droplet := digitalocean.create_droplet(hostname, CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
        database.new_droplet(droplet.id, droplet.hostname)
        loadbalancer.register_droplet(droplet)
        return flask.render_template('webapp.html', message='Your WebApp whill be deployed shortly.')

    return flask.render_template('webapp.html', message='Failed to deploy your WebApp, try again later')