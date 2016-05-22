from scrobbler import app, bcrypt, db, login_manager
from scrobbler.api.views import blueprint as api_bp
from scrobbler.webui.views import blueprint as webui_bp

# Blueprints
app.config.from_pyfile('config.py')
app.register_blueprint(api_bp)
app.register_blueprint(webui_bp, url_prefix='/webui')

# Database
db.init_app(app)

# Authentication
bcrypt.init_app(app)
login_manager.init_app(app)
