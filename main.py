from asyncio.log import logger
import json, logging
import flask, bcrypt, os, hashlib, time, magic, zipfile, io
import database
from digitalocean import DigitalOcean, CloudRegion, CloudImage, CloudSize
from docker import Docker
from loadbalancer import Loadbalancer

app = flask.Flask(__name__)

logging.basicConfig(filename='backend.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

with open('config.json') as f:
    config = json.load(f)

# Flask Config
app.config['SECRET_KEY'] = os.urandom(32).hex()
app.config['TEMPLATES_AUTO_RELOAD'] = True

# File Upload Config
app.config['MAX_CONTENT_PATH'] = (1024 ** 2) * 500 # 500 MB

db = database.Database(config['db']['host'], config['db']['user'], config['db']['pass'], config['db']['db'])
digitalocean = DigitalOcean(config['digitalocean']['api_key'])
loadbalancer = Loadbalancer('10.114.0.3')
docker = Docker(db)

@app.route('/', methods=['GET'])
def index():
    return flask.render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.session.get('customer_id') != None:
        return flask.redirect('/webapp')

    if flask.request.method == 'GET':
        return flask.render_template('login.html')
    else:
        email = flask.request.form.get('email')
        password = flask.request.form.get('password')

        if email == None or password == None:
            return flask.render_template('login.html', code=401)

        customer_id = db.login(email, password)
        
        if customer_id != None:
            flask.session['customer_id'] = customer_id
            return flask.redirect('/webapp')
        
        return flask.render_template('login.html'), 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if flask.session.get('customer_id') != None:
        return flask.redirect('/webapp')

    if flask.request.method == 'GET':
        return flask.render_template('register.html')
    else:
        email = flask.request.form.get('email')
        password = flask.request.form.get('password')
        
        if email == None or password == None:
            return flask.redirect('/register')

        salt = bcrypt.gensalt(12)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt=salt)

        if not db.register(email, password_hash):
            return flask.render_template('register.html'), 500

        return flask.redirect('/webapp')

@app.route('/webapp', methods=['GET', 'POST'])
def webapp():
    customer_id = flask.session.get('customer_id')

    if customer_id == None:
        return flask.redirect('/login', code=401)

    if flask.request.method == 'GET':
        return flask.render_template('webapp.html', customer_id=customer_id)
    else:
        domain = flask.request.form.get('domain')
        file = flask.request.files.get('file')

        if file == None or domain == None:
            return flask.render_template('webapp.html'), 400

        file_bytes = file.stream.read()
        allowed_types = ['application/zip']

        if magic.from_buffer(file_bytes, mime=True) not in allowed_types:
            return flask.render_template('webapp.html'), 400

        buffer = io.BytesIO(file_bytes)
        with zipfile.ZipFile(buffer, 'r', zipfile.ZIP_DEFLATED, False) as f:
            f.extractall(f'/var/www/{domain}')

        if not db.add_webapp(customer_id, domain):
            return flask.render_template('webapp.html'), 500

        # Create container for app
        container = None
        droplet = None
        droplets = db.droplets(active=True)

        if not len(droplets) > 0 and len(db.droplets(active=False)) <= 0:
            hostname = f'app-node-{len(droplets)+1}'
            droplet = digitalocean.create_droplet(hostname, CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node'])
        
            if droplet != None:
                if db.register_droplet(droplet):
                    return flask.render_template('webapp.html', message='Your WebApp will be deployed soon.')
                else: return flask.render_template('webapp.html'), 500
            else: return flask.render_template('webapp.html'), 500

        for droplet_id in droplets:

            droplet = digitalocean.droplet(droplet_id)

            if droplet == None:
                return flask.render_template('webapp.html'), 500

            try:
                container = docker.create(domain, droplet)
                container.start()
                break
            except Exception as e:
                logging.error(e)
                return flask.render_template('webapp.html'), 500

        if container != None and droplet != None:
            loadbalancer.add_domain(domain, container)
            loadbalancer.add_domain(domain, droplet)

        return flask.render_template('webapp.html')

@app.route('/userdata-callback', methods=['GET'])
def callback():
    droplet_id = flask.request.args.get('droplet_id')
    secret = flask.request.args.get('secret')

    if secret == '80c5e536eec8387cccad28b8b17b933832244998d85918abf18cc9bada5d4fe9' and droplet_id != None:

        droplet = digitalocean.droplet(droplet_id)
        if droplet != None:
            db.activate_droplet(droplet)

            for webapp in db.webapps(active=False):
                try:
                    container = docker.create(webapp.get('domain'), droplet)
                    container.start()

                    loadbalancer.add_domain(webapp.get('domain'), container)
                    loadbalancer.add_domain(webapp.get('domain'), droplet)
                    db.activate_webapp(webapp.get('domain'))
                except Exception as e:
                    logger.error(e)

            return flask.jsonify({'data': 'success'})

    return flask.jsonify({'data': 'failed'}), 500

if __name__ == '__main__':
    app.run()