#!/bin/bash

# Package Installation.
apt update -y
apt install nginx docker.io nfs-common -y

# NFS Configuration
mount -t nfs 10.114.0.2:/var/www /var/www
mount -t nfs 10.114.0.2:/home/backend/Amogus/nginx/droplet-loadbalancer /etc/nginx/sites-enabled
echo '10.114.0.2:/var/www/ /var/www  nfs _netdev 0' >> /etc/fstab
echo '10.114.0.2:/home/backend/Amogus/nginx/droplet-loadbalancer /etc/nginx/sites-enabled  nfs _netdev 0' >> /etc/fstab

# Swap Memory Configuration.
fallocate -l 4G /swapfile
dd if=/dev/zero of=/swapfile bs=512M count=8
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap    swap    defaults    0   0' >> /etc/fstab

# Enables the REST API for the docker engine.
sed -i 's/fd:\/\//fd:\/\/ -H tcp:\/\/0.0.0.0:2375/g' /lib/systemd/system/docker.service
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

# User Creation & Setup
PASSWORD=$(cat /dev/urandom | tr -dc '[:alpha:]' | fold -w ${1:-32} | head -1)
useradd -d /home/cloudman -s /bin/bash -p $(openssl passwd -1 $PASSWORD) cloudman
mkdir /home/cloudman && cp -rT /etc/skel /home/cloudman
mkdir /home/cloudman/.ssh && echo 'BACKEND_SSH_KEY' >> /home/cloudman/.ssh/authorized_keys && chmod 600 /home/cloudman/.ssh/authorized_keys
chown -R cloudman:cloudman /home/cloudman
echo 'cloudman ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx' >> /etc/sudoers

# Callback to backend to verify droplet setup.
droplet_id=$(curl -s http://169.254.169.254/metadata/v1.json | python3 -c "import sys, json; print(json.load(sys.stdin)['droplet_id'])")
curl "http://10.114.0.2/userdata-callback?secret=80c5e536eec8387cccad28b8b17b933832244998d85918abf18cc9bada5d4fe9&droplet_id=$droplet_id"