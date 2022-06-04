import droplets, os

def flush():
    os.system('ssh -o "StrictHostKeyChecking no" cloudman@10.114.0.3 "sudo systemctl reload nginx"')

def add_upstream(domain : str, droplet : 'droplets.Droplet'):
    with open(f'nginx/upstreams/{domain}', 'w+') as f:
        config = f.readlines()

        if not len(config) > 0:
            config = [f'upstream {domain}', '{', '}']

        config.insert(2,f'\tserver {droplet.private_ip};')

        f.writelines(config)
    flush()

def remove_upstream(domain : str, droplet : 'droplets.Droplet'):
    with open(f'nginx/upstreams/{domain}', 'w+') as f:
        config = f.readlines()
        config = [x for x in config if f'server {droplet.private_ip}' not in x]

        f.writelines(config)
    flush()

def add_vhost(domain : str):
    with open(f'nginx/vhosts/{domain}', 'w+') as f:
        config = [f'include /etc/nginx/upstreams/{domain};', 'server', '{', f'\tserver_name {domain} www.{domain};', '\tlocation /', '\t{', f'\t\tproxy_pass http://{domain};', '\t}' '}']
        f.writelines(config)
    flush()

def remove_vhost(domain : str):
    if os.path.exists(f'nginx/vhosts/{domain}'):
        os.remove(f'nginx/vhosts/{domain}')
    
    if os.path.exists(f'nginx/upstreams/{domain}'):
        os.remove(f'nginx/upstreams/{domain}')
    flush()