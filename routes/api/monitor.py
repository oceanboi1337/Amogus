import flask, random, logging
from extensions import database, docker, digitalocean, loadbalancer
from models import CloudImage, CloudRegion, CloudSize

router = flask.Blueprint('monitor', __name__)

@router.route('/monitor', methods=['POST'])
def post():
    container_id = flask.request.form.get('container')
    load = float(flask.request.form.get('load'))

    logging.debug(f'Container: {container_id}: {load}')

    if (webapp := database.container_app(container_id)) and (db_droplet := database.container_to_droplet(container_id)):

            inactive_droplets = database.droplets(active=False)
            active_droplets = database.droplets(active=True)

            for droplet in active_droplets:

                droplet = digitalocean.fetch_droplet(droplet.get('id'))

                if droplet == None:
                    continue

                if load > droplet.cpu_limit and droplet.available_slots() > 0:
                    logging.error('Has enough slots')
                    if container := docker.create(webapp.get('domain'), droplet):
                        logging.error('Made a new container')
                        database.new_container(webapp.get('domain'), container.id, droplet.id)
                        loadbalancer.add(webapp.get('domain'), container)
                        loadbalancer.add(webapp.get('domain'), droplet)
                        return flask.jsonify({'success': True})
                    else:
                        logging.error('Failed to create container')

                elif load > droplet.cpu_limit and len(inactive_droplets) <= 0:
                    if droplet := digitalocean.create_droplet(f'app-node-{len(inactive_droplets)+len(active_droplets)}', CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
                        database.new_droplet(droplet.id, droplet.hostname)
                        loadbalancer.register_droplet(droplet)
                        return flask.jsonify({'success', True})
                        
                elif load <= (droplet.cpu_limit * 0.3) and len(database.webapp_containers(webapp.get('domain'))) > 1:
                    if container := docker.container(container_id, droplet):
                        if container.delete():

                            database.delete_container(container_id)
                            loadbalancer.remove(webapp.get('domain'), container)

                            if droplet.available_slots() <= 0 and digitalocean.delete(droplet):
                                database.delete_droplet(droplet.id)
                                loadbalancer.remove(None, droplet)
                                return flask.jsonify({'success', True})
