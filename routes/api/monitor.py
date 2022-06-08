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
                    logging.debug('Has enough slots')
                    if container := docker.create(webapp.get('domain'), droplet):
                        logging.debug('Made a new container')
                        database.new_container(webapp.get('domain'), container.id, droplet.id)
                        loadbalancer.add(webapp.get('domain'), container)
                        loadbalancer.add(webapp.get('domain'), droplet)
                        return flask.jsonify({'success': True})
                    else:
                        logging.debug('Failed to create container')

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
                                loadbalancer.remove(droplet)
                                return flask.jsonify({'success', True})

    return flask.jsonify({'success': False}), 200
    """container_id = flask.request.form.get('container')

    if webapp := database.container_app(container_id):

        logging.debug(webapp)
        domain = webapp[0].get('domain')

        droplets = database.droplets()

        for droplet in droplets:

            if (droplet := digitalocean.fetch_droplet(droplet.get('id'))) == None:
                continue

            if droplet.available_slots() > 0: # Implement later

                if container := docker.create(domain, droplet):

                    database.new_container(domain, container.id, droplet.id)
                    database.activate_webapp(domain)

                    loadbalancer.add(domain, container)
                    loadbalancer.add(domain, droplet)
                    return flask.jsonify({'success': True}), 201

        if droplets == [] and not len(database.droplets(active=False)) > 0:
            if droplet := digitalocean.create_droplet('app-node-1', CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
                database.new_droplet(droplet.id, droplet.hostname)
                loadbalancer.register_droplet(droplet)
                return flask.jsonify({'success': True}), 202

    else:
        return flask.jsonify({'success': False}), 404"""

@router.route('/monitor', methods=['DELETE'])
def delete():
    container_id = flask.request.form.get('container')

    if webapp := database.container_app(container_id):
        if (containers := database.webapp_containers(webapp[0].get('domain'))) and len(containers) > 1:

            container = random.choice(containers)

            if droplet := digitalocean.fetch_droplet(container.get('droplet')):
                if container := docker.container(container.get('container'), droplet):

                    if container.delete():
                        database.delete_container(container.id)
                        loadbalancer.remove(webapp[0].get('domain'), container)

                        if droplet.available_slots() == droplet.container_limit and digitalocean.delete(droplet):
                            database.delete_droplet()
                            loadbalancer.remove(None, droplet)

                        return flask.jsonify({'success': True})
        else:
            return flask.jsonify({'success': False, 'data': 'blacklist'})
    else:
        return flask.jsonify({'success': False}), 404