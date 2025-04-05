from app import db
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
    languageS = db.Column(db.String(100))
    book_id = db.Column(db.String(255))
    download_link = db.Column(db.String(255))
    is_free = db.Column(db.Boolean, default=False)
    preview_link = db.Column(db.String(255))
    thumbnail = db.Column(db.String(255))
    description = db.Column(db.Text)
    source = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preference_id': self.preference_id,
            'title': self.title,
            'author': self.author,
            'genre': self.genre,
            'publication_year': self.publication_year,
            'language': self.languageS,
            'book_id': self.book_id,
            'download_link': self.download_link,
            'is_free': self.is_free,
            'preview_link': self.preview_link,
            'thumbnail': self.thumbnail,
            'description': self.description,
            'source': self.source,
            'created_at': self.created_at.isoformat()
        } 