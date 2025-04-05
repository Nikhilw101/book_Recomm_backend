import requests
import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class BookAPI:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_BOOKS_API_KEY')
        self.google_books_base_url = "https://www.googleapis.com/books/v1/volumes"

    def search_books(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for books using Google Books API
        """
        try:
            params = {
                'q': query,
                'key': self.google_api_key,
                'maxResults': 20
            }
            response = requests.get(self.google_books_base_url, params=params)
            data = response.json()

            if 'items' not in data:
                return []

            books = []
            for item in data['items']:
                volume_info = item.get('volumeInfo', {})
                access_info = item.get('accessInfo', {})
                
                book = {
                    'title': volume_info.get('title', ''),
                    'author': ', '.join(volume_info.get('authors', ['Unknown'])),
                    'genre': ', '.join(volume_info.get('categories', ['Unknown'])),
                    'publication_year': volume_info.get('publishedDate', '')[:4] if volume_info.get('publishedDate') else None,
                    'language': volume_info.get('language', 'en'),
                    'book_id': item.get('id', ''),
                    'download_link': access_info.get('pdf', {}).get('downloadLink', ''),
                    'is_free': access_info.get('pdf', {}).get('isAvailable', False),
                    'preview_link': volume_info.get('previewLink', ''),
                    'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail', ''),
                    'description': volume_info.get('description', ''),
                    'source': 'google_books'
                }
                books.append(book)

            # Apply filters if provided
            if filters:
                books = self._apply_filters(books, filters)

            return books
        except Exception as e:
            print(f"Error searching books: {str(e)}")
            return []

    def _apply_filters(self, books: List[Dict], filters: Dict) -> List[Dict]:
        filtered_books = books.copy()

        if 'is_free' in filters:
            filtered_books = [book for book in filtered_books if book['is_free'] == filters['is_free']]

        if 'sort_by' in filters:
            if filters['sort_by'] == 'price':
                filtered_books.sort(key=lambda x: not x['is_free'])  # Free books first
            elif filters['sort_by'] == 'year':
                filtered_books.sort(key=lambda x: x['publication_year'] if x['publication_year'] else 0, reverse=True)

        return filtered_books

    def get_book_details(self, book_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific book
        """
        try:
            response = requests.get(f"{self.google_books_base_url}/{book_id}")
            data = response.json()
            volume_info = data.get('volumeInfo', {})
            access_info = data.get('accessInfo', {})

            return {
                'title': volume_info.get('title', ''),
                'author': ', '.join(volume_info.get('authors', ['Unknown'])),
                'genre': ', '.join(volume_info.get('categories', ['Unknown'])),
                'publication_year': volume_info.get('publishedDate', '')[:4] if volume_info.get('publishedDate') else None,
                'language': volume_info.get('language', 'en'),
                'book_id': book_id,
                'download_link': access_info.get('pdf', {}).get('downloadLink', ''),
                'is_free': access_info.get('pdf', {}).get('isAvailable', False),
                'preview_link': volume_info.get('previewLink', ''),
                'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail', ''),
                'description': volume_info.get('description', ''),
                'source': 'google_books'
            }
        except Exception as e:
            print(f"Error getting book details: {str(e)}")
            return None 