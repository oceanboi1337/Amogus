# Packages
apt install nfs-kernel-server -y

# User Setup
chown -R backend:backend /var/www

# NFS Server
mkdir -p /home/backend/Amogus/nginx/droplet-loadbalancer
mkdir -p /home/backend/Amogus/nginx/main-loadbalancer
chown -R backend:backend

echo '/home/backend/Amogus/nginx 10.114.0.0/20(ro,sync,subtree_check)' >> /etc/exports
echo '/var/www 10.114.0.0/20(ro,sync,no_subtree_check)' >> /etc/exports

exportfs -a
systemctl restart nfs-kernel-server

# Firewall Rules
ufw default deny incoming
ufw allow ssh
ufw allow http
ufw allow from 10.114.0.0/20 proto tcp to any port 2049
ufw enable