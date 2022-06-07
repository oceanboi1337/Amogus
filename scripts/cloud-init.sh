#!/bin/bash

# Metadata
PRIVATE_IP=$(curl -s http://169.254.169.254/metadata/v1.json | python3 -c "import sys, json; print(json.load(sys.stdin)['interfaces']['private'][0]['ipv4']['ip_address'])")
DROPLET_ID=$(curl -s http://169.254.169.254/metadata/v1.json | python3 -c "import sys, json; print(json.load(sys.stdin)['droplet_id'])")

# Package Installation.
apt update -y
apt install nginx docker.io nfs-common -y

# User Creation & Setup
adduser cloudman --disabled-password --gecos ""
mkdir /home/cloudman/.ssh && echo 'BACKEND_SSH_KEY' >> /home/cloudman/.ssh/authorized_keys
chmod 600 /home/cloudman/.ssh/authorized_keys
chown -R cloudman:cloudman /home/cloudman
echo 'cloudman ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx' >> /etc/sudoers

# NFS Configuration
mkdir /home/cloudman/scripts && chown -R cloudman:cloudman /home/cloudman/scripts
echo '10.114.0.2:/var/www/ /var/www  nfs _netdev 0' >> /etc/fstab # ( ͡° ͜ʖ ͡°) MonkaS
echo "10.114.0.2:/home/backend/Amogus/nginx/droplet-loadbalancer/$DROPLET_ID /etc/nginx/sites-enabled  nfs _netdev 0" >> /etc/fstab
echo '10.114.0.2:/home/backend/Amogus/scripts/remote /home/cloudman/scripts  nfs _netdev 0' >> /etc/fstab
mount -a

# Swap Memory Configuration.
fallocate -l 4G /swapfile
dd if=/dev/zero of=/swapfile bs=512M count=8
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap    swap    defaults    0   0' >> /etc/fstab

# Enables the REST API for the docker engine.
sed -i "s/fd:\/\//fd:\/\/ -H tcp:\/\/$PRIVATE_IP:2375/g" /lib/systemd/system/docker.service
systemctl daemon-reload
systemctl restart docker.service

# Download Nginx docker image.
docker pull nginx:alpine

# Firewall Configuration.
ufw default deny incoming
ufw allow ssh
ufw allow http
ufw allow from 10.114.0.2 to any port 2375
ufw enable

# Callback to backend to verify droplet setup.
curl "http://10.114.0.2/userdata-callback?secret=80c5e536eec8387cccad28b8b17b933832244998d85918abf18cc9bada5d4fe9&droplet_id=$DROPLET_ID"