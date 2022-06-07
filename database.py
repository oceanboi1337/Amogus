from ctypes import Union
import pymysql, pymysql.cursors, logging, bcrypt, time
from typing import Dict, List

class MySQL_Helper:
    def __init__(self, host, user, password, db) -> None:
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            db=db,
            cursorclass=pymysql.cursors.DictCursor
        )

    def execute(self, sql : str, params : List = []) -> dict:
        cursor = self.connection.cursor()
        results = tuple()

        try:
            cursor.execute(sql, params)
            self.connection.commit()
            results = cursor.fetchall()
            results = results if not cursor.lastrowid else cursor.lastrowid
        except Exception as e:
            self.connection.rollback()
            logging.error(f'SQL: {sql}\n{params}\n{e}')
        finally:
            cursor.close()
            return results

class Database(MySQL_Helper):
    def __init__(self, host, user, password, db) -> None:
        super().__init__(host, user, password, db)

    def new_droplet(self, id : str, hostname : str) -> bool:
        return bool(self.execute('INSERT INTO droplets (id, hostname, created_at) VALUES (%s, %s, %s)', [id, hostname, time.time()]))

    def droplet_exists(self, droplet_id) -> bool:
        return bool(self.execute('SELECT id FROM droplets WHERE id=%s', [droplet_id]))

    def verify_droplet(self, droplet_id : str, private_ip : str, public_ip : str) -> bool:
        return bool(self.execute('UPDATE droplets SET public_ip=%s, private_ip=%s, active=%s WHERE id=%s', [private_ip, public_ip, 1, droplet_id]))

    def droplets(self, active=True):
        return self.execute('SELECT * FROM droplets WHERE active=%s', [active])

    def login(self, email : str, password : str) -> int:
        if resp := self.execute('SELECT id, password FROM customers WHERE email=%s LIMIT 1', [email]):
            if bcrypt.checkpw(password.encode(), resp[0].get('password').encode()):
                return resp[0].get('id')
        return None

    def register(self, email, password) -> bool:
        return bool(self.execute('INSERT INTO customers (email, password) VALUES (%s, %s)', [email, password]))

    def add_webapp(self, customer_id : int, domain : str) -> bool:
        return bool(self.execute('INSERT INTO webapps (customer_id, domain) VALUES (%s, %s)', [customer_id, domain]))

    def activate_webapp(self, domain : str) -> bool:
        return bool(self.execute('UPDATE webapps SET active=1 WHERE domain=%s', [domain]))

    def webapps(self, active=True):
        return self.execute('SELECT * FROM webapps WHERE active=%s', [1 if active else 0])

    def new_container(self, domain : str, container_id : str, droplet_id : str) -> bool:
        return bool(self.execute('INSERT INTO containers (id, droplet, webapp) SELECT %s, %s, webapps.id FROM webapps WHERE webapps.domain=%s', [container_id, droplet_id, domain]))

    def container_app(self, container_id : str):
        return self.execute('SELECT * FROM webapps INNER JOIN containers ON webapps.id=containers.webapp AND containers.id=%s', [container_id])