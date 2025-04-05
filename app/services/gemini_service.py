import google.generativeai as genai
from typing import Dict, Any

class GeminiService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def generate_book_description(self, book_details: Dict[str, Any]) -> Dict[str, str]:
        prompt = f"""You are an expert book reviewer and assistant. Your task is to analyze and describe books in a way that is engaging, informative, and easy to understand.

Here is the book's information:
- **Title**: {book_details.get('title', 'N/A')}
- **Author**: {book_details.get('author', 'N/A')}
- **Genre**: {book_details.get('genre', 'N/A')}
- **Publication Year**: {book_details.get('publication_year', 'N/A')}
- **Language**: {book_details.get('language', 'N/A')}

IMPORTANT: You must provide your response in THREE SEPARATE SECTIONS, with each section clearly marked and separated. Each section should be in its respective language.

SECTION 1 - ENGLISH:
1. Introduction and Significance
2. Plot Summary (without spoilers)
3. Main Themes and Messages
4. Writing Style and Literary Techniques
5. Target Audience and Reading Experience
6. Final Verdict and Recommendation

SECTION 2 - HINDI:
1. परिचय और महत्व
2. कथानक सारांश (स्पॉइलर के बिना)
3. मुख्य विषय और संदेश
4. लेखन शैली और साहित्यिक तकनीक
5. लक्षित पाठक और पठन अनुभव
6. अंतिम निर्णय और सिफारिश

SECTION 3 - MARATHI:
1. परिचय आणि महत्त्व
2. कथानक सारांश (स्पॉइलर शिवाय)
3. मुख्य विषय आणि संदेश
4. लेखन शैली आणि साहित्यिक तंत्र
5. लक्षित वाचक आणि वाचन अनुभव
6. अंतिम निर्णय आणि शिफारिश

IMPORTANT FORMATTING RULES:
1. Each section must start with "SECTION X - LANGUAGE:"
2. Each section must be completely separate from the others
3. Do not mix languages within sections
4. Each section should be a complete, standalone analysis"""

        try:
            # Generate content without safety settings
            response = self.model.generate_content(prompt)
            
            # Get the response text
            response_text = response.text
            
            # Debug print
            print("Raw response:", response_text)
            
            # Split the response into different languages using the section markers
            sections = response_text.split('SECTION')
            
            # Extract each language section
            english_section = ""
            hindi_section = ""
            marathi_section = ""
            
            for section in sections:
                section = section.strip()
                if "ENGLISH:" in section:
                    english_section = section.replace("ENGLISH:", "").strip()
                elif "HINDI:" in section:
                    hindi_section = section.replace("HINDI:", "").strip()
                elif "MARATHI:" in section:
                    marathi_section = section.replace("MARATHI:", "").strip()
            
            # If no sections were found, try to use the entire response
            if not any([english_section, hindi_section, marathi_section]):
                english_section = response_text
                hindi_section = "Hindi translation not available"
                marathi_section = "Marathi translation not available"
            
            # Format the response
            return {
                "description": {
                    "english": english_section or "English analysis not available",
                    "hindi": hindi_section or "Hindi analysis not available",
                    "marathi": marathi_section or "Marathi analysis not available"
                },
                "title": book_details.get('title', 'N/A')
            }
            
        except Exception as e:
            print(f"Error in generate_book_description: {str(e)}")
            return {
                "description": {
                    "error": f"Failed to generate book description: {str(e)}",
                    "english": "Error generating English analysis",
                    "hindi": "Error generating Hindi analysis",
                    "marathi": "Error generating Marathi analysis"
                },
                "title": book_details.get('title', 'N/A')
            } 