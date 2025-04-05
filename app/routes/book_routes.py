from flask import Blueprint, request, jsonify
from app.models.book import Book
from app.db import db

book_routes = Blueprint('books', __name__)

@book_routes.route('/', methods=['GET'])
def get_books():
    books = Book.query.all()
    return jsonify([{"id": book.id, "title": book.title, "author": book.author} for book in books]), 200

@book_routes.route('/<int:id>', methods=['GET'])
def get_book(id):
    book = Book.query.get(id)
    if not book:
        return jsonify({"message": "Book not found!"}), 404
    
    return jsonify({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "download_link": book.download_link
    }), 200
