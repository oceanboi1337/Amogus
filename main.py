import flask, os, logging

logging.basicConfig(filename='backend.log', level=logging.DEBUG, format='%(asctime)s,%(msecs)d %(levelname)-8s [%(pathname)s:%(lineno)d in function %(funcName)s]\n%(message)s')
app = flask.Flask(__name__, static_folder='static')

# Flask Config
app.config['SECRET_KEY'] = os.urandom(32).hex()
app.config['TEMPLATES_AUTO_RELOAD'] = True

# File Upload Config
app.config['MAX_CONTENT_PATH'] = (1024 ** 2) * 500 # 500 MB

# Python fuckery to dynamically load flask blueprints
for root, dirs, files in os.walk('routes'):
    for name in [file.replace('.py', '') for file in files if '.py' in file and '__' not in file and '.pyc' not in file]:

        path = os.path.join(root, name)
        prefix = '/' + '/'.join(root.split('/')[1:])

        os.path.join(prefix, name)

        try:
            module = __import__(path.replace('/', '.'), fromlist=['router'])
            router: flask.Blueprint = getattr(module, 'router')

            app.register_blueprint(router, url_prefix=prefix, name=name)
        except Exception as e:
            logging.error(e, module)