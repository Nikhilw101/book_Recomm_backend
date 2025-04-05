from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
import re
from app.models.book import Book
from app.models.bookpreferences import BookPreference
from app.db import db
from flask import current_app

class BookRecommendationModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 3),  # Consider phrases up to 3 words
            max_features=5000,   # Increase feature space
            min_df=2,           # Minimum document frequency
            max_df=0.95         # Maximum document frequency
        )
        self.book_vectors = None
        self.books = []
        self.series_keywords = {
            'brave new world': ['brave new world', 'brave new world revisited', 'huxley'],
            'dune': ['dune', 'dune messiah', 'children of dune', 'god emperor of dune'],
            'harry potter': ['harry potter', 'philosopher stone', 'chamber secrets', 'prisoner azkaban']
        }
        self.last_training = None
        self.training_threshold = timedelta(hours=1)  # Retrain every hour

    def preprocess_text(self, text):
        """Clean and normalize text data"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = ' '.join(text.split())
        return text
    
    def create_book_features(self, book):
        """Create feature vector for a book with enhanced feature engineering"""
        features = []
        
        if isinstance(book, dict):
            # Title features with semantic analysis
            if 'title' in book:
                title = book['title'].lower()
                # Add full title with higher weight
                features.extend([title] * 4)
                # Add individual words (weighted)
                words = [w for w in title.split() if len(w) > 2]
                for word in words:
                    features.extend([word] * 2)
            
            # Author features with name components
            if 'author' in book:
                authors = [a.strip().lower() for a in book['author'].split(',')]
                for author in authors:
                    # Full name with higher weight
                    features.extend([author] * 3)
                    # Individual name parts
                    name_parts = [p for p in author.split() if len(p) > 2]
                    for part in name_parts:
                        features.extend([part] * 2)
            
            # Genre features with hierarchy
            if 'genre' in book:
                genres = [g.strip().lower() for g in book['genre'].split(',')]
                for genre in genres:
                    # Full genre with higher weight
                    features.extend([genre] * 2)
                    # Genre components
                    genre_parts = [p for p in genre.split() if len(p) > 2]
                    for part in genre_parts:
                        features.extend([part])
            
            # Year features with decade grouping
            if 'publication_year' in book:
                year = str(book['publication_year'])
                features.append(year)
                # Add decade
                if year.isdigit():
                    decade = year[:3] + "0"
                    features.append(decade)
            
            # Language features with hierarchy
            if 'languages' in book:
                languages = [l.strip().lower() for l in book['languages'].split(',')]
                for lang in languages:
                    features.append(lang)
                    # Add language family (e.g., 'eng' -> 'english')
                    if lang == 'eng':
                        features.append('english')
                    elif lang == 'spa':
                        features.append('spanish')
                    # Add more language mappings as needed
            
            # URL features for better matching
            if 'thumbnail' in book and book['thumbnail']:
                features.append('has_thumbnail')
            if 'preview_link' in book and book['preview_link']:
                features.append('has_preview')
            if 'download_link' in book and book['download_link']:
                features.append('has_download')
        else:
            # Handle object input with same enhanced features
            if hasattr(book, 'title'):
                title = book.title.lower()
                features.extend([title] * 4)
                words = [w for w in title.split() if len(w) > 2]
                for word in words:
                    features.extend([word] * 2)
            
            if hasattr(book, 'author'):
                authors = [a.strip().lower() for a in book.author.split(',')]
                for author in authors:
                    features.extend([author] * 3)
                    name_parts = [p for p in author.split() if len(p) > 2]
                    for part in name_parts:
                        features.extend([part] * 2)
            
            if hasattr(book, 'genre'):
                genres = [g.strip().lower() for g in book.genre.split(',')]
                for genre in genres:
                    features.extend([genre] * 2)
                    genre_parts = [p for p in genre.split() if len(p) > 2]
                    for part in genre_parts:
                        features.extend([part])
            
            if hasattr(book, 'publication_year'):
                year = str(book.publication_year)
                features.append(year)
                if year.isdigit():
                    decade = year[:3] + "0"
                    features.append(decade)
            
            if hasattr(book, 'languages'):
                languages = [l.strip().lower() for l in book.languages.split(',')]
                for lang in languages:
                    features.append(lang)
                    if lang == 'eng':
                        features.append('english')
                    elif lang == 'spa':
                        features.append('spanish')
            
            # URL features for better matching
            if hasattr(book, 'thumbnail') and book.thumbnail:
                features.append('has_thumbnail')
            if hasattr(book, 'preview_link') and book.preview_link:
                features.append('has_preview')
            if hasattr(book, 'download_link') and book.download_link:
                features.append('has_download')
        
        return ' '.join(features)

    def needs_training(self):
        """Check if model needs retraining"""
        if not self.last_training:
            return True
        return datetime.utcnow() - self.last_training > self.training_threshold

    def fit(self, books=None):
        """Train the model on a list of books"""
        try:
            if not books:
                # Get all books from database
                books = Book.query.all()
                
            if not books:
                current_app.logger.warning("No books found in database for training")
                return
                
            self.books = books
            current_app.logger.info(f"Training model with {len(books)} books")
            
            # Create feature vectors for all books
            self.book_vectors = self.vectorizer.fit_transform(
                [self.create_book_features(book) for book in books]
            )
            self.last_training = datetime.utcnow()
            
            current_app.logger.info("Model training completed successfully")
            
        except Exception as e:
            current_app.logger.error(f"Error in model training: {str(e)}")
            raise

    def get_user_preferences(self, user_id):
        """Get user's book preferences"""
        try:
            preferences = BookPreference.query.filter_by(user_id=user_id).all()
            if not preferences:
                return None
                
            # Aggregate preferences
            genre_weights = defaultdict(float)
            author_weights = defaultdict(float)
            language_weights = defaultdict(float)
            
            for pref in preferences:
                if pref.genre:
                    for genre in pref.genre.split(','):
                        genre_weights[genre.strip().lower()] += 1
                if pref.author:
                    for author in pref.author.split(','):
                        author_weights[author.strip().lower()] += 1
                if pref.language:
                    for lang in pref.language.split(','):
                        language_weights[lang.strip().lower()] += 1
            
            return {
                'genres': dict(genre_weights),
                'authors': dict(author_weights),
                'languages': dict(language_weights)
            }
        except Exception as e:
            current_app.logger.error(f"Error getting user preferences: {str(e)}")
            return None

    def get_recommendations(self, user_books, n_recommendations=10):
        """Get personalized book recommendations with enhanced similarity calculation"""
        if not user_books:
            return []
            
        try:
            # Create feature vectors for all books
            book_features = [self.create_book_features(book) for book in user_books]
            
            # Create TF-IDF vectors
            self.book_vectors = self.vectorizer.fit_transform(book_features)
            
            # Convert to dense array for calculations
            dense_vectors = self.book_vectors.toarray()
            
            # Calculate weighted average user vector with recency bias
            weights = np.linspace(1, 0.5, len(user_books))  # Recent books get higher weight
            user_vector = np.average(dense_vectors, axis=0, weights=weights)
            
            # Calculate cosine similarity with additional metrics
            similarities = cosine_similarity(
                user_vector.reshape(1, -1),
                dense_vectors
            ).flatten()
            
            # Add recency bonus
            recency_bonus = np.linspace(1.2, 1.0, len(user_books))
            similarities = similarities * recency_bonus
            
            # Get indices of most similar books
            similar_indices = similarities.argsort()[-n_recommendations:][::-1]
            
            # Create recommendations with weights
            recommendations = []
            for idx in similar_indices:
                book = user_books[idx]
                weight = similarities[idx]
                
                # Create features repeated by weight
                features = []
                if isinstance(book, dict):
                    if 'title' in book:
                        features.extend([book['title'].lower()] * int(weight * 10))
                    if 'author' in book:
                        authors = [a.strip().lower() for a in book['author'].split(',')]
                        for author in authors:
                            features.extend([author] * int(weight * 8))
                    if 'genre' in book:
                        genres = [g.strip().lower() for g in book['genre'].split(',')]
                        for genre in genres:
                            features.extend([genre] * int(weight * 6))
                    if 'publication_year' in book:
                        features.extend([str(book['publication_year'])] * int(weight * 4))
                    if 'languages' in book:
                        languages = [l.strip().lower() for l in book['languages'].split(',')]
                        for lang in languages:
                            features.extend([lang] * int(weight * 2))
                    
                    recommendations.append({
                        'title': book.get('title', ''),
                        'author': book.get('author', ''),
                        'genre': book.get('genre', ''),
                        'publication_year': book.get('publication_year', ''),
                        'languages': book.get('languages', ''),
                        'download_link': book.get('download_link', ''),
                        'preview_link': book.get('preview_link', ''),
                        'thumbnail': book.get('thumbnail', ''),
                        'weight': weight,
                        'features': ' '.join(features)
                    })
                else:
                    if hasattr(book, 'title'):
                        features.extend([book.title.lower()] * int(weight * 10))
                    if hasattr(book, 'author'):
                        authors = [a.strip().lower() for a in book.author.split(',')]
                        for author in authors:
                            features.extend([author] * int(weight * 8))
                    if hasattr(book, 'genre'):
                        genres = [g.strip().lower() for g in book.genre.split(',')]
                        for genre in genres:
                            features.extend([genre] * int(weight * 6))
                    if hasattr(book, 'publication_year'):
                        features.extend([str(book.publication_year)] * int(weight * 4))
                    if hasattr(book, 'languages'):
                        languages = [l.strip().lower() for l in book.languages.split(',')]
                        for lang in languages:
                            features.extend([lang] * int(weight * 2))
                    
                    recommendations.append({
                        'title': getattr(book, 'title', ''),
                        'author': getattr(book, 'author', ''),
                        'genre': getattr(book, 'genre', ''),
                        'publication_year': getattr(book, 'publication_year', ''),
                        'languages': getattr(book, 'languages', ''),
                        'download_link': getattr(book, 'download_link', ''),
                        'preview_link': getattr(book, 'preview_link', ''),
                        'thumbnail': getattr(book, 'thumbnail', ''),
                        'weight': weight,
                        'features': ' '.join(features)
                    })
            
            # Sort recommendations by weight
            recommendations.sort(key=lambda x: x['weight'], reverse=True)
            
            # Remove weight and features from final output
            for rec in recommendations:
                del rec['weight']
                del rec['features']
            
            return recommendations
            
        except Exception as e:
            current_app.logger.error(f"Error in get_recommendations: {str(e)}")
            return []
    
    def get_similar_books(self, book_id, n_similar=5):
        """Get similar books to a specific book"""
        if not self.book_vectors or not self.books:
            return []
        
        try:
            # Find the index of the target book
            target_idx = self.books.index(book_id)
            
            # Convert to dense array for similarity calculation
            dense_vectors = self.book_vectors.toarray()
            
            # Calculate cosine similarity with all other books
            similarities = cosine_similarity(
                dense_vectors[target_idx:target_idx+1],
                dense_vectors
            ).flatten()
            
            # Get indices of similar books (excluding the target book)
            similar_indices = np.argsort(similarities)[-n_similar-1:-1][::-1]
            
            # Get similar books
            similar_books = [self.books[i] for i in similar_indices]
            
            return similar_books
            
        except Exception as e:
            current_app.logger.error(f"Error in get_similar_books: {str(e)}")
            return [] 