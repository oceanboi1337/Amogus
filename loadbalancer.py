from typing import List, Union
from digitalocean import Droplet
from docker import Container
import os, logging, subprocess

class Loadbalancer:
    def __init__(self, loadbalancers : List[str]) -> None:
        self.loadbalancers = loadbalancers

    def indent(self, config : List[str]):
        indentation = 0
        config = [x for x in config if x != '']
        for index, line in enumerate(config):
            if line == '}': indentation -= 1
            config[index] = ('\t' * indentation) + line
            if line == '{': indentation += 1

        return '\n'.join(config)

    def reload(self, node : Union[Droplet, Container]):
        private_ip = node.droplet.private_ip if type(node) == Container else node
        cmd = f'ssh -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" cloudman@{private_ip} "sudo systemctl reload nginx"'
        
        # Check if the node is a container, this will make it so only that app-host server gets reloaded.
        if type(node) == Container:
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Check if the node is a app-host, this will reload every load balancer available.
        elif type(node) == Droplet:
            for host in self.loadbalancers:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Loadbalance the loadbalancer later?

    def register_droplet(self, droplet : Droplet):
        path = f'nginx/container-loadbalancer/{droplet.id}'
        if not os.path.exists(path):
            os.mkdir(path)

    def add(self, domain : str, node : Union[Droplet, Container]):
        if type(node) == Droplet or type(node) == Container:
            
            # The path is changed based on the type of node passed to the function.
            # If the node is a load balancer, the path will be changed to nginx/droplet-loadbalancer
            # If the node is a app-host, the path will be changed to nginx/container-loadbalancer/app-host-id/example.com
            path = f'nginx/droplet-loadbalancer/{domain}' if type(node) == Droplet else f'nginx/container-loadbalancer/{node.droplet.id}/{domain}'
            mode = 'w+' if not os.path.exists(path) else 'r+'

            # Open the nginx config file
            with open(path, mode) as f:

                # Split the config file by newline and check if the app-host / container ip is already added to the config.
                if (config := f.read().replace('\t', '').split('\n')) and mode == 'r+':
                    if f'server {node.private_ip};' not in config:
                        config.insert(2, f'server {node.private_ip};')
                    config = self.indent(config) # Make the config output pretty :3
                else:
                    with open('nginx/example.conf', 'r') as tmp:
                        config = tmp.read().replace('example.com', domain).replace('127.0.0.1', node.private_ip)

                f.seek(0) # Move the file cursor to the start to overwrite the current config with the updated one.
                f.write(config)
                f.truncate() # Truncate the remaining data in the config file just in case the config is smaller.

        self.reload(node)

    def remove(self, domain : str, node : Union[Droplet, Container]):
        if type(node) == Droplet or type(node) == Container:
            path = f'nginx/droplet-loadbalancer/{domain}' if type(node) == Droplet else f'nginx/container-loadbalancer/{node.droplet.id}/{domain}'
            mode = 'w+' if not os.path.exists(path) else 'r+'

            with open(path, mode) as f:
                config = f.read().replace('\t', '').split('\n')
                config = [x for x in config if node.private_ip not in x]

                if 'server ' not in ''.join(config):
                    f.close()
                    os.remove(path)
                else:
                    f.seek(0)
                    f.write(self.indent(config))
                    f.truncate()
        """elif type(node) == Droplet:
            path = f'nginx/droplet-loadbalancer/{node.id}'
            if os.path.exists(path):
                os.remove(path)"""

        self.reload(node)