import flask, random
from extensions import database, docker, digitalocean, loadbalancer
from models import CloudImage, CloudRegion, CloudSize

router = flask.Blueprint('monitor', __name__)

@router.route('/monitor', methods=['POST'])
def post():
    container_id = flask.request.form.get('id')

    if webapp := database.container_app(container_id):

        domain = webapp[0].get('domain')

        if (droplets := database.droplets(active=True)) == [] and not len(database.droplets(active=False)) > 0:
            if droplet := digitalocean.create_droplet('app-node-1', CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
                database.new_droplet(droplet.id, droplet.hostname)
                loadbalancer.register_droplet(droplet)
                return flask.jsonify({'success': True}), 202

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

        hostname = f'app-node-{len(droplets)+1}'
        if droplet := digitalocean.create_droplet(hostname, CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
            database.new_droplet(droplet.id, droplet.hostname)
            loadbalancer.register_droplet(droplet)
            return flask.jsonify({'success': True}), 202

@router.route('/monitor', methods=['DELETE'])
def delete():
    container_id = flask.request.form.get('id')

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