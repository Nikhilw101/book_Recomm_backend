from flask import Blueprint, request, jsonify
from app.services.gemini_service import GeminiService
import os

book_assistant_routes = Blueprint('book_assistant', __name__)

# Initialize Gemini service with API key
GEMINI_API_KEY = "AIzaSyDgxQNnsxs35NorPl78EM-jlRy-QRmDJeo"
gemini_service = GeminiService(GEMINI_API_KEY)

@book_assistant_routes.route('/book-assistant', methods=['POST'])
def get_book_assistant():
    try:
        book_details = request.get_json()
        
        if not book_details:
            return jsonify({
                "error": "No book details provided"
            }), 400
            
        # Generate book description using Gemini
        description = gemini_service.generate_book_description(book_details)
        
        return jsonify({
            "title": book_details.get('title'),
            "description": description
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to process request: {str(e)}"
        }), 500 