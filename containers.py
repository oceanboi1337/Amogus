import requests, droplets, database, loadbalancer
from typing import List
from cloud_enums import CloudRegion, CloudSize, CloudImage

class Container:
    def __init__(self, droplet : 'droplets.Droplet', id : str) -> None:
        self.id = id
        self.droplet = droplet
        self.api = self.droplet.docker_endpoint
        self.session = requests.Session()

        self.private_ip = None

    def start(self) -> bool:
        resp = requests.post(f'{self.droplet.docker_endpoint}/containers/{self.id}/start')

        if resp.status_code == 204:
            resp = self.session.get(f'{self.api}/containers/{self.id}/json')
            if resp.status_code == 200:
                self.private_ip = resp.json()['NetworkSettings']['IPAddress']
                return True
        return False

class ContainerManager:
    def __init__(self, db : 'database.Database', droplet_manager : 'droplets.DropletManager') -> None:
        self.db = db
        self.droplet_manager = droplet_manager
        self.s = requests.Session()

    def containers(self):
        for droplet in self.droplet_manager.droplets(tags=['app-node']):
            print(droplet.id)

    def create(self, domain : str, memory=512, cpu=0.5, retries=0) -> Container:
        container = None
        error = False

        #droplets = [droplet for droplet in self.droplet_manager.droplets(tags=['app-node']) if droplet.container_slots() > 0]

        droplets = self.db.active_droplets()
        for droplet in droplets:

            droplet = self.droplet_manager.fetch(droplet)

            if not droplet.available_containers() > 0:
                continue

            data = {
                'Image': 'nginx:alpine',
                'HostConfig': { 'Binds': [f'/var/www/{domain}:/usr/share/nginx/html'] }
            }

            resp = self.s.post(f'{droplet.docker_endpoint}/containers/create', json=data)

            if resp.status_code == 201:

                container = Container(droplet, resp.json()['Id'])
                container.start()

                droplet.add_vhost(domain, container.private_ip)
                droplet.exec('sudo systemctl reload nginx')

                return container
            else:
                error = True
                print(f'Error while creating container ({resp.status_code}):\n{resp.text}')
        
        if container == None and error == False:

            name = f'app-node-{len(droplets)+1}'

            droplet = self.droplet_manager.create(
                name=name,
                region=CloudRegion.Frankfurt1,
                size=CloudSize.Cpu2Gb2,
                image=CloudImage.Ubuntu_22_04_LTS_x64,
                tags=['app-node'],
                monitoring=True,
                ssh_keys=[
                    'f4:bb:99:fe:80:77:fb:ff:1c:e7:3c:dd:12:9c:9c:af',  # System Administrator Public Key
                    '25:67:80:9a:18:f3:b7:cb:be:db:f7:5e:06:50:14:29'   # Backend Server Public Key
                ]
            )

        return None