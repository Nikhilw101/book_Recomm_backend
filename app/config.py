from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize SQLAlchemy
db = SQLAlchemy()

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)  # Random key for session handling
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://sql12773552:VqZDxVM4Hv@sql12.freesqldatabase.com:3306/sql12773552'


def create_app():
    app = Flask(__name__)

    # Load the config
    app.config.from_object(Config)

    # Initialize the db with the app
    db.init_app(app)

    # Register blueprints or routes
    from app.routes.auth_routes import auth_routes
    app.register_blueprint(auth_routes, url_prefix='/auth')

    return app
