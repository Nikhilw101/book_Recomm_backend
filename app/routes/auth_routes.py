from flask import Blueprint, request, jsonify
from app.models.user import User
from app.db import db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from app.config import Config  # Assuming you have a config file for secret key

auth_routes = Blueprint('auth_routes', __name__)

# Register User Route
@auth_routes.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password') or not data.get('username') or not data.get('name'):
        return jsonify({"error": "Missing required fields"}), 400

    # Using the default method 'pbkdf2:sha256'
    hashed_password = generate_password_hash(data['password'])  # No need to specify method

    new_user = User(email=data['email'], username=data['username'], password=hashed_password, name=data['name'])

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Login User Route
@auth_routes.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=data['email']).first()

    if user and check_password_hash(user.password, data['password']):
        # Generate JWT token
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expiration in 1 hour
        }, Config.SECRET_KEY, algorithm='HS256')

        return jsonify({"message": "Login successful", "token": token, "user_id": user.id}), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401
