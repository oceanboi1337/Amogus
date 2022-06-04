import requests, database, containers, subprocess, os, loadbalancer
from cloud_enums import CloudRegion, CloudSize, CloudImage
from typing import List

class Image:
    def __init__(self, data) -> None:
        self.id = data.get('id')
        self.name = data.get('name')

class Droplet:
    def __init__(self, data) -> None:
        self.id = data.get('id')
        self.name = data.get('name')
        self.memory = data.get('memory')
        self.vcpus = data.get('vcpus')
        self.disk = data.get('disk')
        self.status = data.get('status')
        self.image = Image(data.get('image'))
        self.public_ip = None
        self.private_ip = None
        self.tags = data.get('tags')

        if len(data.get('networks').get('v4')) > 0:
            self.public_ip = data.get('networks').get('v4')[0].get('ip_address')
        if len(data.get('networks').get('v4')) > 1:
            self.private_ip = data.get('networks').get('v4')[1].get('ip_address')

        self.docker_endpoint = f'http://{self.private_ip}:2375'

    def containers(self):
        resp = requests.get(f'{self.docker_endpoint}/containers/json')
        if resp.status_code == 200:
            return resp.json()

    def exec(self, cmd : str):
        cmd = cmd.replace('"', '\"')
        os.system(f'ssh -o "StrictHostKeyChecking no" cloudman@{self.private_ip} "{cmd}"')

    def available_containers(self):
        return 4 - len(self.containers())

    def add_vhost(self, domain : str, ip_address : str):
        with open('nginx/default.conf', 'r') as f:
            default = f.read()
            domain_config = default.replace('example.com', domain)
            domain_config = domain_config.replace('0.0.0.0', ip_address)

            with open(f'nginx/sites-enabled/{domain}', 'w') as f:
                f.write(domain_config)

        loadbalancer.add_upstream(domain, self)
        loadbalancer.add_vhost(domain)

        self.exec('sudo systemctl reload nginx')

class DropletManager:
    def __init__(self, db : 'database.Database', api_key) -> None:
        self.db = db
        self.api_key = api_key
        self.s = requests.Session()
        self.s.headers['Authorization'] = f'Bearer {self.api_key}'
        self.s.headers['Content-Type'] = 'application/json'
        self.api_endpoint = 'https://api.digitalocean.com/v2'

    def droplets(self, tags=[]) -> List[Droplet]:
        data = None
        resp = None

        if len(tags) > 0:
            tag_names = ':'.join(tags)
            resp = self.s.get(f'{self.api_endpoint}/droplets?page=1&per_page=200&tag_name={tag_names}')
        else:
            resp = self.s.get(f'{self.api_endpoint}/droplets?page=1&per_page=200')

        if resp.status_code == 200:
            data = resp.json()
            return [Droplet(x) for x in data.get('droplets')]
        
        print(f'Failed to fetch from API with status code: {resp.status_code}')
        return None

    def fetch(self, droplet_id : str) -> Droplet:
        resp = self.s.get(f'{self.api_endpoint}/droplets/{droplet_id}')

        if resp.status_code == 200:
            return Droplet(resp.json()['droplet'])
        
        return None

    def create(self, name : str, region : CloudRegion, size : CloudSize, image : CloudImage, tags=[], monitoring=True, ssh_keys=[]) -> Droplet:
        with open('cloud-config.sh', 'r') as f:
            
            resp = self.s.get('https://api.digitalocean.com/v2/account/keys/25:67:80:9a:18:f3:b7:cb:be:db:f7:5e:06:50:14:29')

            backend_ssh_key = resp.json()['ssh_key']['public_key']

            data = {
                'name': name,
                'region': region,
                'size': size,
                'image': image,
                'tags': tags,
                'user_data': f.read().replace('BACKEND_SSH_KEY', backend_ssh_key),
                'ssh_keys': ssh_keys,
                'monitoring': monitoring
            }

        resp = self.s.post(f'{self.api_endpoint}/droplets', json=data, headers={'Content-Type': 'application/json'})

        if resp.status_code == 202:
            droplet = Droplet(resp.json()['droplet'])
            self.db.register_droplet(droplet)
            return droplet

        return None