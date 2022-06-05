from typing import List, Union
from digitalocean import Droplet
from docker import Container
import os, logging

class Loadbalancer:
    def __init__(self, host : str) -> None:
        self.host = host

    def indent_config(self, config : List[str]):
        parsed_config = ''
        indentation = 0

        for x in config:
            if x == '}': indentation -= 1
            parsed_config += ('\t' * indentation) + x + '\n'
            if x == '{': indentation += 1

        return parsed_config

    def reload_nginx(self, node : Union[Droplet, Container]):
        host = self.host if type(node) == Droplet else node.private_ip
        os.system(f'ssh -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" cloudman@{host} "sudo systemctl reload nginx"')

    def add_domain(self, domain : str, node : Union[Droplet, Container]):
        path = f'nginx/main-loadbalancer/{domain}' if type(node) == Droplet else f'nginx/droplet-loadbalancer/{domain}'

        with open(path, 'w+') as f:
            config = f.read().split('\n')
            if len(config) > 1:
                config.insert(2, f'\tserver {node.private_ip};')
            else:
                config = [f'upstream {domain}', '{', f'server {node.private_ip};', '}', 'server', '{', f'server_name {domain} www.{domain};', 'location /', '{', f'proxy_pass http://{domain};', '}', '}']

            f.write(self.indent_config(config))

        self.reload_nginx(node)

    def remove_domain(self, domain : str, node : Union[Droplet, Container]):
        path = f'nginx/main-loadbalancer/{domain}' if type(node) == Droplet else f'nginx/droplet-loadbalancer/{domain}'

        with open(path, 'w+') as f:
            config = f.read().split('\n')
            config = [x for x in config if x != f'server {node.private_ip};']
            f.write(self.indent_config(config))

        self.reload_nginx(node)