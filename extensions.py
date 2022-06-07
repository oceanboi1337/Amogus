from digitalocean import DigitalOcean, Droplet
from loadbalancer import Loadbalancer
from docker import Docker, Container
from database import Database
import config

database = Database(config.MYSQL_HOST, config.MYSQL_USER, config.MYSQL_PASS, config.MYSQL_DB)
digitalocean = DigitalOcean(config.DO_API_KEY)
loadbalancer = Loadbalancer(config.LOADBALANCERS)
docker = Docker()