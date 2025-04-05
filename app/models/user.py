from app.db import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255))
    username = db.Column(db.String(255))
    password = db.Column(db.String(255))
    name = db.Column(db.String(255))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    # Relationships
    preferences = db.relationship('BookPreference', back_populates='user', lazy='dynamic')
    books = db.relationship('Book', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"