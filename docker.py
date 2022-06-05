import logging
from typing import List
from xmlrpc.client import Server
import requests, digitalocean

class BadParameter(Exception): pass
class ImageNotFound(Exception): pass
class Conflict(Exception): pass
class ServerError(Exception): pass

class Container:
    def __init__(self, droplet : 'digitalocean.Droplet', id : str) -> None:
        self.droplet = droplet
        self.id = id
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

class Docker:   
    def __init__(self, database) -> None:
        self.database = database

    def create(self, domain : str, droplet : 'digitalocean.Droplet') -> Container:
        settings = {
            'Image': 'nginx:alpine',
            'HostConfig': { 'Bind': [f'/var/www/{domain}:/usr/share/nginx/html'] }
        }

        with requests.post(f'http://{droplet.private_ip}:2375/containers/create', json=settings) as resp:
            logging.debug(resp.text)
            if resp.status_code == 201:
                return Container(droplet, resp.json().get('Id'))
            elif resp.status_code == 400:
                raise BadParameter
            elif resp.status_code == 404:
                raise ImageNotFound
            elif resp.status_code == 409:
                raise Conflict
            elif resp.status_code == 500:
                raise ServerError

        raise Exception('Unknown Error')