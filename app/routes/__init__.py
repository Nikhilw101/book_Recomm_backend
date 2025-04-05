from flask import Flask
from app.db import db
from app.config import Config

# The Flask app instance is initialized here.
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
