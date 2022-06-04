import json
import flask, bcrypt, os, hashlib, time, magic, zipfile, io
import database, containers, droplets

app = flask.Flask(__name__)

with open('config.json') as f:
    config = json.load(f)

# Flask Config
app.config['SECRET_KEY'] = os.urandom(32).hex()
app.config['TEMPLATES_AUTO_RELOAD'] = True

# File Upload Config
app.config['MAX_CONTENT_PATH'] = (1024 ** 2) * 500 # 500 MB

db = database.Database(config['db']['host'], config['db']['user'], config['db']['password'], config['db']['db'])
droplet_manager = droplets.DropletManager(db, config['digitalocean']['api_key'])
container_manager = containers.ContainerManager(db, droplet_manager)

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
        container = container_manager.create(domain=domain)

        if container != None:
            db.activate_webapp(domain)
        else:
            return flask.render_template('webapp.html', status='Your WebApp will be deployed shortly.')

        return flask.render_template('webapp.html')

@app.route('/userdata-callback', methods=['GET'])
def callback():
    droplet_id = flask.request.args.get('droplet_id')
    secret = flask.request.args.get('secret')

    if secret == '80c5e536eec8387cccad28b8b17b933832244998d85918abf18cc9bada5d4fe9' and droplet_id != None:

        droplet = droplet_manager.fetch(droplet_id)

        if droplet != None and db.activate_droplet(droplet):
            for webapp in db.webapps(active=False):
                container = container_manager.create(domain=webapp.get('domain'))

                if container != None:
                    db.activate_webapp(domain=webapp.get('domain'))

            return flask.jsonify({'data': 'success'})

    return flask.jsonify({'data': 'failed'}), 500

if __name__ == '__main__':
    app.run()