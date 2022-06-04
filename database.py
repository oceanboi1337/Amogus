import pymysql, pymysql.cursors, time, bcrypt
from typing import List
import containers, droplets

class Database:
    def __init__(self, host, user, password, db) -> None:
        self.connection = pymysql.connect(host=host, user=user, password=password, db=db, cursorclass=pymysql.cursors.DictCursor)

    def register_droplet(self, droplet : 'droplets.Droplet'):
        with self.connection.cursor() as c:
            try:
                c.execute('INSERT INTO droplets (id, name, public_ip, private_ip, active, last_active) VALUES (%s, %s, %s, %s, %s, %s)', [
                    droplet.id,
                    droplet.name,
                    droplet.public_ip,
                    droplet.private_ip,
                    0,
                    0
                ])
                c.connection.commit()
            except Exception as e:
                print(f'Error while registering droplet:\n{e}')
                return False

        return True

    def activate_droplet(self, droplet) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('UPDATE droplets SET public_ip=%s, private_ip=%s, active=%s, last_active=%s', [
                    droplet.public_ip,
                    droplet.private_ip,
                    1, # Set 'active' to true
                    time.time() # Epoch time for 'last_active'
                ])
                c.connection.commit()
            except Exception as e:
                print(f'Error while activating droplet:\n{e}')
                c.connection.rollback()
                return False
        return True

    def active_droplets(self):
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT id FROM droplets WHERE active=1')
                return [x.get('id') for x in c.fetchall()]

            except Exception as e:
                print(f'Error while fetching droplets:\n{e}')
                return []

    def login(self, email, password) -> int:
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT id, password FROM customers WHERE email=%s LIMIT 1', [email])

                row = c.fetchone()
                if row == None:
                    raise Exception('Not found.')
                if bcrypt.checkpw(password.encode(), row.get('password').encode()):
                    return row.get('id')
                else:
                    return None
            except Exception as e:
                print(f'Error while logging in customer {email}:\n{e}')
                return None
        
    def register(self, email, password) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('INSERT INTO customers (email, password) VALUES (%s, %s)', [email, password])
                c.connection.commit()
            except Exception as e:
                print(f'Error while registering customer {email}:\n{e}')
                return False
        return True

    def add_webapp(self, customer_id : int, domain : str) -> bool:
        with self.connection.cursor() as c:
            try:
                c.execute('INSERT INTO webapps (customer_id, domain) VALUES (%s, %s)', [customer_id, domain])
                c.connection.commit()
            except Exception as e:
                print(f'Error while adding webapp to database:\n{e}')
                return False
        return True

    def activate_webapp(self, domain : str):
        with self.connection.cursor() as c:
            try:
                c.execute('UPDATE webapps SET active=1 WHERE domain=%s', [domain])
                c.connection.commit()
            except Exception as e:
                print(f'Error while activating webapp:\n{e}')

    def webapps(self, active=True):
        with self.connection.cursor() as c:
            try:
                c.execute('SELECT * FROM webapps WHERE active=%s', [1 if active else 0])
                return c.fetchall()
            except Exception as e:
                print(f'Error while fetching webapps:\n{e}')