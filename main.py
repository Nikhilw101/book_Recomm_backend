from flask import Flask
from app.db import db, init_db
from app.routes.auth_routes import auth_routes
from app.routes.book_routes import book_routes
from app.routes.recommendation_routes import recommendation_routes
from app.routes.book_assistant_routes import book_assistant_routes
from flask_cors import CORS



def create_app():
    app = Flask(__name__)

    # Configure your app, e.g., database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://sql12773552:VqZDxVM4Hv@sql12.freesqldatabase.com:3306/sql12773552'
  # Change with your MySQL credentials
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable track modifications for performance

    # Initialize the database
    init_db(app)
      
    # Register routes
    app.register_blueprint(auth_routes, url_prefix='/auth')
    app.register_blueprint(book_routes, url_prefix='/books')
    app.register_blueprint(recommendation_routes, url_prefix='/recommendations')
    app.register_blueprint(book_assistant_routes, url_prefix='/book-assistant')
    CORS(app)
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
