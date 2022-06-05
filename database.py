import pymysql, pymysql.cursors, time, bcrypt
from typing import List
from docker import Container
from digitalocean import Droplet

class Database:
    def __init__(self, host, user, password, db) -> None:
        self.connection = pymysql.connect(host=host, user=user, password=password, db=db, cursorclass=pymysql.cursors.DictCursor)

    def register_droplet(self, droplet : Droplet):
        with self.connection.cursor() as c:
            c.execute('INSERT INTO droplets (id, name, public_ip, private_ip, active) VALUES (%s, %s, %s, %s, %s, %s)', [droplet.id, droplet.name, droplet.public_ip, droplet.private_ip, 0])

    def activate_droplet(self, droplet : Droplet):
        with self.connection.cursor() as c:
            c.execute('UPDATE droplets SET public_ip=%s, private_ip=%s, active=%s', [droplet.public_ip, droplet.private_ip, 1])

    def active_droplets(self) -> List[str]:
        with self.connection.cursor() as c:
            c.execute('SELECT id FROM droplets WHERE active=1')
            return [x.get('id') for x in c.fetchall()]

    def login(self, email : str, password : str) -> int:
        with self.connection.cursor() as c:
            c.execute('SELECT id, password FROM customers WHERE email=%s LIMIT 1', [email])

            row = c.fetchone()
            if row != None and bcrypt.checkpw(password.encode(), row.get('password').encode()):
                return row.get('id')
        return None
        
    def register(self, email, password):
        with self.connection.cursor() as c:
            c.execute('INSERT INTO customers (email, password) VALUES (%s, %s)', [email, password])

    def add_webapp(self, customer_id : int, domain : str):
        with self.connection.cursor() as c:
            c.execute('INSERT INTO webapps (customer_id, domain) VALUES (%s, %s)', [customer_id, domain])

    def activate_webapp(self, domain : str):
        with self.connection.cursor() as c:
            c.execute('UPDATE webapps SET active=1 WHERE domain=%s', [domain])

    def webapps(self, active=True):
        with self.connection.cursor() as c:
            c.execute('SELECT * FROM webapps WHERE active=%s', [1 if active else 0])
            return c.fetchall()