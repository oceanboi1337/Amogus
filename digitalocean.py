from models import CloudImage, CloudRegion, CloudSize
from typing import List
import requests, logging

class Droplet:
    def __init__(self, data) -> None:
        self.id = data.get('id') # The ID of the server on DigitalOcean
        self.hostname = data.get('name')
        self.memory = data.get('memory')
        self.vcpus = data.get('vcpus')

        self.container_limit = self.vcpus * 2
        self.cpu_limit = (90 / self.container_limit) # All containers together should only be able to use 90% of the total CPU Usage

        self.session = requests.Session()
        
        self.public_ip = None
        self.private_ip = None

        # The network configuration is only accessible once the server has been booted.
        if len(data.get('networks').get('v4')) > 0:
            self.public_ip = data.get('networks').get('v4')[0].get('ip_address')
            
        if len(data.get('networks').get('v4')) > 1:
            self.private_ip = data.get('networks').get('v4')[1].get('ip_address')

    def available_slots(self) -> int:
        # Send API request to the server's Docker service to get the running containers.
        with self.session.get(f'http://{self.private_ip}:2375/containers/json') as resp:
            if resp.status_code == 200:
                # Return the amount of available container slots, calcualted by ((vCPUs * 2) - Containers Running)
                return self.container_limit - len(resp.json())
        # Return 0 if the Docker API returned an error.
        return 0

class DigitalOcean:
    def __init__(self, api_key : str) -> None:
        self.api_key = api_key
        self.endpoint = 'https://api.digitalocean.com/v2'
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {self.api_key}'

    def create_droplet(self, hostname, size : CloudSize, image : CloudImage, region : CloudRegion, tags : List[str]) -> Droplet:
        with open('scripts/cloud-init.sh', 'r') as f:
            data = {
                'name': hostname,
                'region': region,
                'size': size,
                'image': image,
                'ssh_keys': [
                    'f4:bb:99:fe:80:77:fb:ff:1c:e7:3c:dd:12:9c:9c:af',   # System Administrator
                    'd6:29:bb:63:6e:4f:37:07:e1:f2:9a:92:6d:21:3d:12'    # System Administrator 2
                ],
                'tags': tags,
                'user_data': f.read().replace('BACKEND_SSH_KEY', self.ssh_key('96:9f:f7:09:fc:2d:e7:bb:76:d3:fa:4d:2e:08:42:5b')) # backend@backend
            }
        
        with self.session.post(f'{self.endpoint}/droplets', json=data) as resp:
            if resp.status_code == 202:
                return Droplet(resp.json()['droplet'])
        
        return None

    def delete(self, droplet : Droplet) -> bool:
        with self.session.delete(f'{self.endpoint}/droplets/{droplet.id}') as resp:
            if resp.status_code == 204:
                return True

    def fetch_droplet(self, id : str) -> Droplet:
        with self.session.get(f'{self.endpoint}/droplets/{id}') as resp:
            if resp.status_code == 200:
                return Droplet(resp.json().get('droplet'))

    def ssh_key(self, fingerprint : str):
        with self.session.get(f'{self.endpoint}/account/keys/{fingerprint}') as resp:
            return resp.json()['ssh_key']['public_key']