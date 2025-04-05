from app.db import db
from datetime import datetime

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    preference_id = db.Column(db.Integer, db.ForeignKey('bookpreferences.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100))
    publication_year = db.Column(db.Integer)
    languages = db.Column(db.String(100))
    book_id = db.Column(db.String(255))
    download_link = db.Column(db.String(255))
    is_free = db.Column(db.Boolean, default=False)
    preview_link = db.Column(db.String(255))
    thumbnail = db.Column(db.String(255))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', back_populates='books')
    preference = db.relationship('BookPreference', back_populates='books')

    def __repr__(self):
        return f"<Book(id={self.id}, title={self.title}, author={self.author})>"