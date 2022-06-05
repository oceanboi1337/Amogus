import requests
from typing import List
from enum import Enum

class CloudRegion(str, Enum):
    NewYork1 = 'nyc1'
    SanFrancisco1 = 'sfo1'
    NewYork2 = 'nyc2'
    Amsterdam2 = 'ams2'
    Singapore1 = 'sgp1'
    London1 = 'lon1'
    NewYork3 = 'nyc3'
    Amsterdam3 = 'ams3'
    Frankfurt1 = 'fra1'
    Toronto1 = 'tor1'
    SanFrancisco2 = 'sfo2'
    Bangalore1 = 'blr1'
    SanFrancisco3 = 'sfo3'

class CloudSize(str, Enum):
    Cpu1Gb1 = 's-1vcpu-1gb'
    Cpu1Gb2 = 's-1vcpu-2gb'
    Cpu2Gb2 = 's-2vcpu-2gb'
    Cpu2Gb4 = 's-2vcpu-4gb'

class CloudImage(str, Enum):
    Ubuntu_22_04_LTS_x64 = 'ubuntu-22-04-x64'

class Droplet:
    def __init__(self, data) -> None:
        self.id = data.get('id')
        self.hostname = data.get('name')
        self.memory = data.get('memory')
        self.vcpus = data.get('vcpus')
        
        self.public_ip = None
        self.private_ip = None

        if len(data.get('networks').get('v4')) > 0: self.public_ip = data.get('networks').get('v4')[0].get('ip_address')
        if len(data.get('networks').get('v4')) > 1: self.private_ip = data.get('networks').get('v4')[1].get('ip_address')

class DigitalOcean:
    def __init__(self, api_key : str) -> None:
        self.api_key = api_key
        self.endpoint = 'https://api.digitalocean.com/v2'
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {self.api_key}'

    def droplet(self, id : str):
        with self.session.get(f'{self.endpoint}/droplets/{id}') as resp:
            if resp.status_code == 200:
                return Droplet(resp.json().get('droplet'))
        
        return None

    def create_droplet(self, hostname, size : CloudSize, image : CloudImage, region : CloudRegion, tags : List[str]) -> Droplet:
        pass