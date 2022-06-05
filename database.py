import pymysql, pymysql.cursors, logging, bcrypt
from typing import List
from docker import Container
from digitalocean import Droplet

class Database:
    def __init__(self, host, user, password, db) -> None:
        self.connection = pymysql.connect(host=host, user=user, password=password, db=db, cursorclass=pymysql.cursors.DictCursor)

    def register_droplet(self, droplet : Droplet) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('INSERT INTO droplets (id, hostname, public_ip, private_ip, active) VALUES (%s, %s, %s, %s, %s)', [droplet.id, droplet.hostname, droplet.public_ip, droplet.private_ip, 0])
                c.connection.commit()
                return True
            except Exception as e:
                logging.error(e)

    def activate_droplet(self, droplet : Droplet) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('UPDATE droplets SET public_ip=%s, private_ip=%s, active=%s', [droplet.public_ip, droplet.private_ip, 1])
                c.connection.commit()
                return True
            except Exception as e:
                logging.error(e)

    def droplets(self, active=True) -> List[str]:
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT id FROM droplets WHERE active=%s', [active])
                return [x.get('id') for x in c.fetchall()]
            except Exception as e:
                logging.error(e)

    def login(self, email : str, password : str) -> int:
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT id, password FROM customers WHERE email=%s LIMIT 1', [email])

                row = c.fetchone()
                if row != None and bcrypt.checkpw(password.encode(), row.get('password').encode()):
                    return row.get('id')
            except Exception as e:
                logging.error(e)
        
    def register(self, email, password) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('INSERT INTO customers (email, password) VALUES (%s, %s)', [email, password])
                c.connection.commit()
                return True
            except Exception as e:
                logging.error(e)

    def add_webapp(self, customer_id : int, domain : str) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT * FROM webapps WHERE domain=%s', [domain])
                if len(c.fetchall()) > 0:
                    return False

                c.execute('INSERT INTO webapps (customer_id, domain) VALUES (%s, %s)', [customer_id, domain])
                c.connection.commit()
                return True
            except Exception as e:
                logging.error(e)

    def activate_webapp(self, domain : str):
        with self.connection.cursor() as c:
            try:
                c.execute('UPDATE webapps SET active=1 WHERE domain=%s', [domain])
                c.connection.commit()
            except Exception as e:
                logging.error(e)

    def webapps(self, active=True):
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT * FROM webapps WHERE active=%s', [1 if active else 0])
                return c.fetchall()
            except Exception as e:
                logging.error(e)