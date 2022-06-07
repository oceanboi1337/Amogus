from venv import create
import flask, logging
from extensions import digitalocean, database, docker, loadbalancer
from models import CloudImage, CloudRegion, CloudSize

router = flask.Blueprint('callback', __name__)

@router.route('/callback', methods=['POST'])
def callback():
    if droplet_id := flask.request.form.get('droplet_id'):

        # Check if droplet exists in database.
        if database.droplet_exists(droplet_id):
            
            # Update the newly created droplet in the database with the required values so it can be used.
            if droplet := digitalocean.fetch_droplet(droplet_id):
                database.verify_droplet(droplet.id, droplet.private_ip, droplet.public_ip)

            droplets = [x.get('id') for x in database.droplets()]
            webapps = [x.get('domain') for x in database.webapps(active=False)]

            logging.debug(droplets)

            if len(droplets) > 0:
                for droplet_id in droplets:
                    if (droplet := digitalocean.fetch_droplet(droplet_id)) and droplet.available_slots() > 0:
                        for domain in webapps:
                            if container := docker.create(domain, droplet):
                                loadbalancer.add(domain, container)
                                loadbalancer.add(domain, droplet)
                                database.activate_webapp(domain)
                                database.new_container(domain, container.id, droplet.id)
                                return flask.jsonify({'success': True}), 201
            else:
                hostname = f'app-node-{len(droplets)+1}'
                if droplet := digitalocean.create_droplet(hostname, CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
                    database.new_droplet(droplet, hostname)
                    loadbalancer.register_droplet(droplet)
                    return flask.jsonify({'success': True}), 202
        else:
            return flask.jsonify({'success': False}), 404

    return flask.jsonify({'success': False}), 500