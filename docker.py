import logging
from typing import List
import requests

from digitalocean import Droplet

class BadParameter(Exception): pass
class ImageNotFound(Exception): pass
class Conflict(Exception): pass
class ServerError(Exception): pass

class Container:
    def __init__(self, droplet : 'Droplet', raw_data) -> None:
        self.droplet = droplet
        self.id = raw_data.get('Id')
        self.session = requests.Session()

        self.private_ip = None

    def start(self) -> bool:
        with self.session.post(f'http://{self.droplet.private_ip}:2375/containers/{self.id}/start') as resp:
            if resp.status_code == 204:
                with self.session.get(f'http://{self.droplet.private_ip}:2375/containers/{self.id}/json') as resp:
                    if resp.status_code == 200:
                        self.private_ip = resp.json().get('NetworkSettings').get('IPAddress')
                        return True
        return False

    def delete(self) -> bool:
        with self.session.delete(f'http://{self.droplet.private_ip}:2375/containers/{self.id}?force=true') as resp:
            if resp.status_code == 204:
                return True
        return False

class Docker:
    def __init__(self) -> None:
        self.session = requests.Session()

    def container(self, id : str, droplet : Droplet):
        with self.session.get(f'http://{droplet.private_ip}:2375/containers/{id}/json') as resp:
            if resp.status_code == 200:
                return Container(droplet, resp.json())

    def create(self, domain : str, droplet : 'Droplet', start=True) -> 'Container':
        settings = {
            'Image': 'nginx:alpine',
            'HostConfig': {
                'Binds': [f'/var/www/{domain}:/usr/share/nginx/html'],
                'Memory': (1024 ** 2) * 500,
                'MemorySwap': (1024 ** 3),
                'CpuQuota': 25000
            }
        }

        with self.session.post(f'http://{droplet.private_ip}:2375/containers/create', json=settings) as resp:
            if resp.status_code == 201:
                container = Container(droplet, resp.json())
                if start: container.start()
                return container

            elif resp.status_code == 400: raise BadParameter
            elif resp.status_code == 404: raise ImageNotFound
            elif resp.status_code == 409: raise Conflict
            elif resp.status_code == 500: raise ServerError
        
        raise Exception('Unknown error while creating container')