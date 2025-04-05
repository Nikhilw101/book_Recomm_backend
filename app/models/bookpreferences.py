from app.db import db

class BookPreference(db.Model):
    __tablename__ = 'bookpreferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(500))
    author = db.Column(db.String(255))
    genre = db.Column(db.String(100))
    publication_year = db.Column(db.Integer)
    language = db.Column(db.String(100))  # New field

    # Relationships
    user = db.relationship('User', back_populates='preferences')
    books = db.relationship('Book', back_populates='preference', lazy='dynamic')

    def __repr__(self):
        return f"<BookPreference(id={self.id}, user_id={self.user_id}, title={self.title})>"