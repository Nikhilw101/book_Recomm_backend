from flask import Blueprint, request, jsonify
from app.models.bookpreferences import BookPreference
from app.models.book import Book
from app.models.user import User
from app.db import db
import requests
import os
from collections import defaultdict
from flask import current_app
from sqlalchemy import or_
from datetime import datetime, timedelta
from app.utils.recommendation_model import BookRecommendationModel
import random

recommendation_routes = Blueprint('recommendation_routes', __name__)

# Initialize the recommendation model
recommendation_model = BookRecommendationModel()

@recommendation_routes.route('/user/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    try:
        # Query user by ID
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID {user_id}"
            }), 404
            
        # Return only user details
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching user details: {str(e)}")
        return jsonify({
            "error": "Failed to fetch user details",
            "message": str(e)
        }), 500

BOOK_APIS = [
    {
        'name': 'google_books',
        'url': 'https://www.googleapis.com/books/v1/volumes',
        'key': os.getenv('GOOGLE_BOOKS_API_KEY'),
        'query_builder': lambda params: {'q': f"intitle:{params.get('title','')} inauthor:{params.get('author','')}"},
        'parser': lambda item: {
            'title': item.get('volumeInfo', {}).get('title', ''),
            'author': ', '.join(item.get('volumeInfo', {}).get('authors', ['Unknown'])),
            'publication_year': item.get('volumeInfo', {}).get('publishedDate', '')[:4] if item.get('volumeInfo', {}).get('publishedDate') else None,
            'genre': ', '.join(item.get('volumeInfo', {}).get('categories', [])),
            'language': item.get('volumeInfo', {}).get('language', 'en'),
            'download_link': item.get('accessInfo', {}).get('pdf', {}).get('downloadLink', ''),
            'preview_link': item.get('volumeInfo', {}).get('previewLink', ''),
            'thumbnail': item.get('volumeInfo', {}).get('imageLinks', {}).get('thumbnail', ''),
            'source': 'google_books'
        }
    },
    {
        'name': 'open_library',
        'url': 'https://openlibrary.org/search.json',
        'key': None,
        'query_builder': lambda params: {
            'title': params.get('title', ''),
            'author': params.get('author', ''),
            'subject': params.get('genre', ''),
            'limit': 5
        },
        'parser': lambda item: {
            'title': item.get('title', ''),
            'author': ', '.join(item.get('author_name', ['Unknown'])),
            'publication_year': str(item.get('first_publish_year', '')),
            'genre': ', '.join(item.get('subject', [])[:3]),
            'language': item.get('language', ['en'])[0] if item.get('language') else 'en',
            'download_link': f"https://openlibrary.org{item.get('key', '')}" if item.get('key') else '',
            'preview_link': f"https://openlibrary.org{item.get('key', '')}",
            'thumbnail': f"https://covers.openlibrary.org/b/id/{item.get('cover_i', '')}-M.jpg" if item.get('cover_i') else '',
            'source': 'open_library'
        }
    }
]

def search_books(params):
    """Search across multiple book APIs"""
    books = []
    
    for api in BOOK_APIS:
        try:
            # Build API-specific query
            query_params = api['query_builder'](params)
            if api['key']:
                query_params['key'] = api['key']
            
            response = requests.get(api['url'], params=query_params, timeout=10)
            response.raise_for_status()
            
            # Parse API-specific response
            if api['name'] == 'google_books':
                items = response.json().get('items', [])[:5]
            elif api['name'] == 'open_library':
                items = response.json().get('docs', [])[:5]
            
            books.extend([api['parser'](item) for item in items])
            
            if books:  # Return if we find results
                return books[:5]
                
        except Exception as e:
            current_app.logger.error(f"Error with {api['name']} API: {str(e)}")
            continue
            
    return books[:5]

@recommendation_routes.route('/preferences', methods=['POST'])
def submit_preferences_and_recommendations():
    data = request.json
    user_id = data.get('user_id')
    search_params = {
        'title': data.get('title'),
        'author': data.get('author'),
        'genre': data.get('genre'),
        'publication_year': data.get('publication_year'),
        'language': data.get('language')
    }
    
    # Save preferences
    preference = BookPreference(user_id=user_id, **search_params)
    db.session.add(preference)
    db.session.commit()

    # Search across multiple APIs
    books = search_books(search_params)

    # Save books to database with available fields and collect their IDs
    saved_book_ids = []
    for book in books:
        new_book = Book(
            user_id=user_id,
            preference_id=preference.id,
            title=book.get('title', ''),
            author=book.get('author', 'Unknown'),
            genre=book.get('genre', ''),
            publication_year=int(book.get('publication_year')) if book.get('publication_year') else None,
            languages=book.get('language', 'en'),
            book_id=book.get('id', ''),
            download_link=book.get('download_link', ''),
            is_free='free' in (book.get('download_link', '')).lower(),
            preview_link=book.get('preview_link', ''),
            thumbnail=book.get('thumbnail', '')
        )
        db.session.add(new_book)
        db.session.flush()  # Flush to get the ID without committing
        saved_book_ids.append(new_book.id)
    
    db.session.commit()

    # Enhance books data with their database IDs
    enhanced_books = []
    for book, book_id in zip(books, saved_book_ids):
        enhanced_book = book.copy()
        enhanced_book['id'] = book_id
        enhanced_books.append(enhanced_book)

    return jsonify({
        "message": "Preferences saved successfully!",
        "recommendations": enhanced_books,
        "user_id": user_id,
        "preference_id": preference.id
    }), 201

# Fetch user book history
@recommendation_routes.route('/history', methods=['GET'])
def get_history():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id parameter is required"}), 400

    history = Book.query.filter_by(user_id=user_id).order_by(Book.created_at.desc()).all()

    if not history:
        return jsonify({"message": "No history found for the user!"}), 404

    result = [
        {
            'id': book.id,
            'user_id': book.user_id,
            'preference_id': book.preference_id,
            'title': book.title,
            'author': book.author,
            'genre': book.genre,
            'publication_year': book.publication_year,
            'languages': book.languages,
            'book_id': book.book_id,
            'download_link': book.download_link,
            'is_free': book.is_free,
            'preview_link': book.preview_link,
            'thumbnail': book.thumbnail,
            'created_at': book.created_at.isoformat() if book.created_at else None
        }
        for book in history
    ]
    return jsonify({
        "count": len(result),
        "history": result
    }), 200

@recommendation_routes.route('/history/<int:book_id>', methods=['DELETE'])
def delete_book_from_history(book_id):
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id parameter is required"}), 400

        # Find the book and verify it belongs to the user
        book = Book.query.filter_by(id=book_id, user_id=user_id).first()
        
        if not book:
            return jsonify({"error": "Book not found or unauthorized"}), 404

        # Delete the book
        db.session.delete(book)
        db.session.commit()

        return jsonify({
            "message": "Book deleted successfully",
            "book_id": book_id
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting book: {str(e)}")
        return jsonify({
            "error": "Failed to delete book",
            "message": str(e)
        }), 500

@recommendation_routes.route('/debug', methods=['GET'])
def debug_state():
    try:
        # Get total books in database
        total_books = Book.query.count()
        current_app.logger.info(f"Total books in database: {total_books}")
        
        # Get books for specific user
        user_id = request.args.get('user_id')
        if user_id:
            user_books = Book.query.filter_by(user_id=user_id).all()
            current_app.logger.info(f"Books for user {user_id}: {len(user_books)}")
            
            # Log some sample books
            for book in user_books[:3]:
                current_app.logger.info(f"Sample book: {book.title} by {book.author}")
        
        # Get user preferences
        if user_id:
            preferences = BookPreference.query.filter_by(user_id=user_id).all()
            current_app.logger.info(f"Preferences for user {user_id}: {len(preferences)}")
            
            # Log sample preferences
            for pref in preferences[:3]:
                current_app.logger.info(f"Sample preference: {pref.genre} by {pref.author}")
        
        return jsonify({
            "total_books": total_books,
            "user_books": len(user_books) if user_id else 0,
            "user_preferences": len(preferences) if user_id else 0,
            "message": "Debug information retrieved successfully"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({
            "error": "Failed to get debug information",
            "message": str(e)
        }), 500

@recommendation_routes.route('/auto-recommend', methods=['GET'])
def auto_recommend():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id parameter is required"}), 400

        # Get user's reading history
        user_books = Book.query.filter_by(user_id=user_id).order_by(Book.id.desc()).all()

        if not user_books:
            return jsonify({
                "recommendations": [],
                "message": "No reading history found"
            }), 200

        current_app.logger.info(f"Found {len(user_books)} books in user history")
        
        # Analyze user's reading patterns
        reading_patterns = analyze_reading_patterns(user_books)
        
        # Get personalized recommendations from model
        recommended_books = recommendation_model.get_recommendations(user_books, n_recommendations=15)
        current_app.logger.info(f"Model generated {len(recommended_books)} recommendations")
        
        # Get dynamic external recommendations based on user patterns
        external_recommendations = get_dynamic_external_recommendations(reading_patterns)
        
        # Search for additional book details using the search_books function
        enhanced_recommendations = []
        for book in recommended_books:
            search_params = {
                'title': book.get('title', ''),
                'author': book.get('author', '')
            }
            # Get additional details from APIs
            api_books = search_books(search_params)
            if api_books:
                # Find the best matching book from API results
                best_match = next(
                    (api_book for api_book in api_books 
                     if api_book['title'].lower() == book['title'].lower() 
                     and api_book['author'].lower() == book['author'].lower()),
                    None
                )
                if best_match:
                    # Create new book entry with API data
                    enhanced_book = {
                        'title': book.get('title', ''),
                        'author': book.get('author', ''),
                        'genre': book.get('genre', ''),
                        'publication_year': book.get('publication_year', ''),
                        'language': book.get('language', 'en'),
                        'download_link': best_match.get('download_link', ''),
                        'preview_link': best_match.get('preview_link', ''),
                        'thumbnail': best_match.get('thumbnail', ''),
                        'source': 'enhanced_model'
                    }
                    enhanced_recommendations.append(enhanced_book)
                else:
                    # If no API match, create book entry with empty URLs
                    enhanced_book = {
                        'title': book.get('title', ''),
                        'author': book.get('author', ''),
                        'genre': book.get('genre', ''),
                        'publication_year': book.get('publication_year', ''),
                        'language': book.get('language', 'en'),
                        'download_link': '',
                        'preview_link': '',
                        'thumbnail': '',
                        'source': 'model'
                    }
                    enhanced_recommendations.append(enhanced_book)
            else:
                # If no API results, create book entry with empty URLs
                enhanced_book = {
                    'title': book.get('title', ''),
                    'author': book.get('author', ''),
                    'genre': book.get('genre', ''),
                    'publication_year': book.get('publication_year', ''),
                    'language': book.get('language', 'en'),
                    'download_link': '',
                    'preview_link': '',
                    'thumbnail': '',
                    'source': 'model'
                }
                enhanced_recommendations.append(enhanced_book)
        
        # Combine with external recommendations
        all_recommendations = combine_and_enhance_recommendations(enhanced_recommendations, external_recommendations)
        
        # Get dynamic metadata based on user patterns
        metadata = generate_dynamic_metadata(reading_patterns)
        
        # Format recommendations with additional details
        formatted_recommendations = []
        for rec in all_recommendations[:10]:
            formatted_rec = {
                'title': rec.get('title', ''),
                'author': rec.get('author', ''),
                'genre': rec.get('genre', ''),
                'publication_year': rec.get('publication_year', ''),
                'language': rec.get('language', 'en'),
                'download_link': rec.get('download_link', ''),
                'preview_link': rec.get('preview_link', ''),
                'thumbnail': rec.get('thumbnail', ''),
                'source': rec.get('source', 'model')
            }
            formatted_recommendations.append(formatted_rec)
        
        return jsonify({
            "recommendations": formatted_recommendations,
            "message": "Successfully generated personalized recommendations",
            "metadata": metadata
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in auto_recommend: {str(e)}")
        return jsonify({
            "error": "Failed to generate recommendations",
            "message": str(e)
        }), 500

def analyze_reading_patterns(user_books):
    """Analyze user's reading patterns to understand preferences"""
    patterns = {
        'genres': defaultdict(float),
        'authors': defaultdict(float),
        'time_periods': defaultdict(float),
        'languages': defaultdict(float),
        'price_preferences': defaultdict(float),
        'title_patterns': defaultdict(float),
        'author_series': defaultdict(float),
        'content_type': defaultdict(float)
    }
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    for idx, book in enumerate(user_books):
        recency_weight = 1.0 + (idx / len(user_books)) * 0.5
        
        if book.genre:
            for genre in [g.strip().lower() for g in book.genre.split(',')]:
                patterns['genres'][genre] += recency_weight
        
        if book.author:
            for author in [a.strip().lower() for a in book.author.split(',')]:
                patterns['authors'][author] += recency_weight
                if any(kw in book.title.lower() for kw in ['book', 'series', 'part']):
                    patterns['author_series'][author] += recency_weight
        
        if book.publication_year:
            try:
                decade = (int(book.publication_year) // 10) * 10
                patterns['time_periods'][f"{decade}s"] += recency_weight
            except ValueError:
                pass
        
        if book.languages:
            for lang in [l.strip().lower() for l in book.languages.split(',')]:
                patterns['languages'][lang] += recency_weight
        
        if book.download_link:
            dl_lower = book.download_link.lower()
            patterns['price_preferences']['free' if 'free' in dl_lower or 'gutenberg' in dl_lower else 'paid'] += recency_weight
        
        if book.title:
            for word in [w.lower() for w in book.title.split() if len(w) > 2]:
                patterns['title_patterns'][word] += recency_weight
        
        if book.genre:
            genres = [g.strip().lower() for g in book.genre.split(',')]
            fiction_keywords = {'fiction', 'novel', 'story', 'tale'}
            patterns['content_type']['fiction' if any(k in g for g in genres for k in fiction_keywords) else 'non-fiction'] += recency_weight
    
    for category in patterns:
        if patterns[category]:
            max_weight = max(patterns[category].values())
            patterns[category] = {k: v/max_weight for k, v in patterns[category].items()}
    
    return patterns

def get_dynamic_external_recommendations(reading_patterns):
    """Get external recommendations from APIs"""
    external_recommendations = []
    
    for api in BOOK_APIS:
        try:
            query_components = []
            preferences = []
            
            # Build query based on strongest preferences
            top_authors = sorted(reading_patterns['authors'].items(), key=lambda x: x[1], reverse=True)[:2]
            if top_authors:
                preferences.append((' OR '.join(f'inauthor:"{a}"' for a, _ in top_authors), top_authors[0][1]))
            
            top_series = sorted(reading_patterns['author_series'].items(), key=lambda x: x[1], reverse=True)[:1]
            if top_series:
                preferences.append((f'inauthor:"{top_series[0][0]}"', top_series[0][1]))
            
            top_genres = sorted(reading_patterns['genres'].items(), key=lambda x: x[1], reverse=True)[:2]
            if top_genres:
                preferences.append((' OR '.join(f'subject:"{g}"' for g, _ in top_genres), top_genres[0][1]))
            
            top_periods = sorted(reading_patterns['time_periods'].items(), key=lambda x: x[1], reverse=True)[:1]
            if top_periods:
                preferences.append((f'publishedDate:{top_periods[0][0]}', top_periods[0][1]))
            
            content_type = max(reading_patterns['content_type'].items(), key=lambda x: x[1])
            preferences.append((f'subject:"{content_type[0]}"', content_type[1]))
            
            price_pref = max(reading_patterns['price_preferences'].items(), key=lambda x: x[1])
            if price_pref[0] == 'free':
                preferences.append(('filter:free-ebooks', price_pref[1]))
            
            preferences.sort(key=lambda x: x[1], reverse=True)
            query_components = [p[0] for p in preferences[:3]]
            
            if query_components:
                api_params = {'q': ' AND '.join(query_components)}
                if api['key']:
                    api_params['key'] = api['key']
                
                response = requests.get(api['url'], params=api_params, timeout=10)
                response.raise_for_status()
                
                items = response.json().get('items' if api['name'] == 'google_books' else 'docs', [])[:5]
                
                scored_items = []
                for item in items:
                    # Use the API's parser to get all book details including URLs
                    book = api['parser'](item)
                    score = 0
                    
                    # Calculate score based on user preferences
                    if book['title']:
                        score += sum(reading_patterns['title_patterns'].get(w, 0) 
                                   for w in set(book['title'].lower().split()) if len(w) > 2)
                    
                    if book['author']:
                        score += sum(reading_patterns['authors'].get(a.strip().lower(), 0) 
                                   for a in book['author'].split(','))
                    
                    if book['genre']:
                        score += sum(reading_patterns['genres'].get(g.strip().lower(), 0) 
                                   for g in book['genre'].split(','))
                    
                    if book['language']:
                        score += reading_patterns['languages'].get(book['language'].lower(), 0)
                    
                    if book.get('download_link'):
                        is_free = 'free' in book['download_link'].lower() or 'gutenberg' in book['download_link'].lower()
                        score += reading_patterns['price_preferences'].get('free' if is_free else 'paid', 0)
                    
                    scored_items.append((book, score))
                
                external_recommendations.extend([item[0] for item in sorted(scored_items, key=lambda x: x[1], reverse=True)[:5]])
                
        except Exception as e:
            current_app.logger.error(f"Error with {api['name']} API: {str(e)}")
            continue
    
    return external_recommendations

def combine_and_enhance_recommendations(model_recommendations, external_recommendations):
    """Combine and enhance recommendations with external data"""
    all_recommendations = []
    seen_titles = set()
    
    # First pass: Enhance model recommendations with external data
    enhanced_model_recs = []
    for model_rec in model_recommendations:
        # Find matching external book (case-insensitive comparison)
        matched_external = next(
            (ext for ext in external_recommendations 
             if ext['title'].lower() == model_rec['title'].lower() 
             and ext['author'].lower() == model_rec['author'].lower()),
            None
        )
        
        # Create enhanced recommendation with all available data
        enhanced_rec = {
            'title': model_rec['title'],
            'author': model_rec['author'],
            'genre': model_rec.get('genre', ''),
            'publication_year': model_rec.get('publication_year', ''),
            'language': model_rec.get('language', 'en'),
            'download_link': matched_external.get('download_link', '') if matched_external else model_rec.get('download_link', ''),
            'preview_link': matched_external.get('preview_link', '') if matched_external else model_rec.get('preview_link', ''),
            'thumbnail': matched_external.get('thumbnail', '') if matched_external else model_rec.get('thumbnail', ''),
            'source': 'enhanced_model' if matched_external else 'model'
        }
        enhanced_model_recs.append(enhanced_rec)
    
    # Second pass: Add enhanced model recommendations
    for book in enhanced_model_recs:
        if book['title'] not in seen_titles:
            seen_titles.add(book['title'])
            all_recommendations.append(book)
    
    # Third pass: Add remaining external recommendations
    for book in external_recommendations:
        if book['title'] not in seen_titles:
            seen_titles.add(book['title'])
            # Ensure all required fields are present
            enhanced_book = {
                'title': book['title'],
                'author': book['author'],
                'genre': book.get('genre', ''),
                'publication_year': book.get('publication_year', ''),
                'language': book.get('language', 'en'),
                'download_link': book.get('download_link', ''),
                'preview_link': book.get('preview_link', ''),
                'thumbnail': book.get('thumbnail', ''),
                'source': 'external'
            }
            all_recommendations.append(enhanced_book)
    
    return all_recommendations

def generate_dynamic_metadata(reading_patterns):
    """Generate metadata about user's reading patterns"""
    return {
        "top_genres": [g[0] for g in sorted(reading_patterns['genres'].items(), key=lambda x: x[1], reverse=True)[:3]],
        "top_authors": [a[0] for a in sorted(reading_patterns['authors'].items(), key=lambda x: x[1], reverse=True)[:2]],
        "preferred_time_periods": [p[0] for p in sorted(reading_patterns['time_periods'].items(), key=lambda x: x[1], reverse=True)[:2]],
        "preferred_languages": [l[0] for l in sorted(reading_patterns['languages'].items(), key=lambda x: x[1], reverse=True)[:2]],
        "price_preferences": dict(sorted(reading_patterns['price_preferences'].items(), key=lambda x: x[1], reverse=True)),
        "content_type_preferences": dict(sorted(reading_patterns['content_type'].items(), key=lambda x: x[1], reverse=True)),
        "reading_patterns": {
            "genre_diversity": len(reading_patterns['genres']),
            "author_diversity": len(reading_patterns['authors']),
            "time_period_diversity": len(reading_patterns['time_periods']),
            "language_diversity": len(reading_patterns['languages']),
            "series_preference": bool(reading_patterns['author_series']),
            "title_pattern_diversity": len(reading_patterns['title_patterns'])
        }
    }