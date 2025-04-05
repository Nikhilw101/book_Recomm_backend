from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.book_preferences import BookPreference
from app.models.books import Book
from app import db
from app.utils.book_api import BookAPI

book_preferences_bp = Blueprint('book_preferences', __name__)
book_api = BookAPI()

@book_preferences_bp.route('/api/book-preferences', methods=['POST'])
@jwt_required()
def create_book_preference():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Create book preference
        preference = BookPreference(
            user_id=user_id,
            title=data.get('title'),
            author=data.get('author'),
            genre=data.get('genre'),
            publication_year=data.get('publication_year'),
            language=data.get('language')
        )
        db.session.add(preference)
        db.session.commit()

        # Search for books using the preference
        search_query = f"{data.get('title', '')} {data.get('author', '')}"
        filters = {
            'is_free': data.get('is_free', None),
            'sort_by': data.get('sort_by', None)
        }
        
        books = book_api.search_books(search_query, filters)

        # Save matching books to database
        for book_data in books:
            book = Book(
                user_id=user_id,
                preference_id=preference.id,
                title=book_data['title'],
                author=book_data['author'],
                genre=book_data['genre'],
                publication_year=book_data['publication_year'],
                languageS=book_data['language'],
                book_id=book_data['book_id'],
                download_link=book_data['download_link'],
                is_free=book_data['is_free'],
                preview_link=book_data['preview_link'],
                thumbnail=book_data['thumbnail'],
                description=book_data['description'],
                source=book_data['source']
            )
            db.session.add(book)
        
        db.session.commit()

        return jsonify({
            'message': 'Book preference created successfully',
            'preference': preference.to_dict(),
            'books': [book.to_dict() for book in books]
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@book_preferences_bp.route('/api/book-preferences/<int:preference_id>/books', methods=['GET'])
@jwt_required()
def get_books_for_preference(preference_id):
    try:
        user_id = get_jwt_identity()
        preference = BookPreference.query.filter_by(id=preference_id, user_id=user_id).first()
        
        if not preference:
            return jsonify({'error': 'Book preference not found'}), 404

        # Get filter parameters
        is_free = request.args.get('is_free', type=bool)
        sort_by = request.args.get('sort_by')

        # Query books with filters
        query = Book.query.filter_by(preference_id=preference_id)
        
        if is_free is not None:
            query = query.filter_by(is_free=is_free)
        
        if sort_by == 'price':
            query = query.order_by(Book.is_free.desc())
        elif sort_by == 'year':
            query = query.order_by(Book.publication_year.desc())

        books = query.all()

        return jsonify({
            'preference': preference.to_dict(),
            'books': [book.to_dict() for book in books]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@book_preferences_bp.route('/api/book-preferences/<int:preference_id>/books/<int:book_id>', methods=['GET'])
@jwt_required()
def get_book_details(preference_id, book_id):
    try:
        user_id = get_jwt_identity()
        book = Book.query.filter_by(
            id=book_id,
            preference_id=preference_id,
            user_id=user_id
        ).first()
        
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        # Get additional details from the source API
        book_details = book_api.get_book_details(book.book_id, book.source)
        
        if book_details:
            return jsonify({
                'book': book.to_dict(),
                'details': book_details
            }), 200
        else:
            return jsonify({'error': 'Could not fetch book details'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@book_preferences_bp.route('/api/book-preferences', methods=['GET'])
@jwt_required()
def get_user_preferences():
    try:
        user_id = get_jwt_identity()
        preferences = BookPreference.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'preferences': [pref.to_dict() for pref in preferences]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500 