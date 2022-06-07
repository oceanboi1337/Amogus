from typing import List, Union
from digitalocean import Droplet
from docker import Container
import os, logging

class Loadbalancer:
    def __init__(self, loadbalancers : List[str]) -> None:
        self.loadbalancers = loadbalancers

    def indent(self, config : List[str]):
        output = ''
        indentation = 0

        for x in config:
            if x == '}': indentation -= 1
            output += ('\t' * indentation) + x + '\n'
            if x == '{': indentation += 1

        return output

    # Clean later.
    def reload(self, node : Union[Droplet, Container]):
        if type(node) == Container:
            os.system(f'/bin/ssh -i ~/.ssh/id_rsa -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" cloudman@{node.droplet.private_ip} "sudo systemctl reload nginx"')
        elif type(node) == Droplet:
            for host in self.loadbalancers:
                os.system(f'/bin/ssh -i ~/.ssh/id_rsa -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" cloudman@{host} "sudo systemctl reload nginx"')
        
        # Loadbalance the loadbalancer later.

    def register_droplet(self, droplet : Droplet):
        path = f'nginx/container-loadbalancer/{droplet.id}'
        if not os.path.exists(path):
            os.mkdir(path)

    def add(self, domain : str, node : Union[Droplet, Container]):
        if type(node) == Droplet or type(node) == Container:
            path = f'nginx/droplet-loadbalancer/{domain}' if type(node) == Droplet else f'nginx/container-loadbalancer/{node.droplet.id}/{domain}'
            mode = 'w+' if not os.path.exists(path) else 'r+'

            with open(path, mode) as f:
                if (config := f.read().replace('\t', '').split('\n')) and mode == 'r+':
                    if f'server {node.private_ip};' not in config:
                        config.insert(2, f'server {node.private_ip};')
                    config = self.indent(config)
                else:
                    with open('nginx/example.conf', 'r') as tmp:
                        config = tmp.read().replace('example.com', domain).replace('127.0.0.1', node.private_ip)

                f.seek(0)
                f.write(config)
                f.truncate()

        self.reload(node)

    def remove(self, domain : str, node : Union[Droplet, Container]):
        if type(node) == Container:
            with open(f'nginx/container-loadbalancer/{node.droplet.id}/{domain}', 'r+') as f:
                config = f.read().replace('\t', '').split('\n')
                config = [x for x in config if node.private_ip not in x]

                if 'server ' not in ''.join(config):
                    f.close()
                    os.remove(f'nginx/container-loadbalancer/{node.droplet.id}/{domain}')
                else:
                    f.seek(0)
                    f.write(self.indent(config))
                    f.truncate()
        elif type(node) == Droplet:
            path = f'nginx/droplet-loadbalancer/{node.id}'
            if os.path.exists(path):
                os.remove(path)

        self.reload(node)