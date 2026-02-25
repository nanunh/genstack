import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

class AIAnalyzer:
    def __init__(self):
        self.analysis_prompts = {
            'summary': "Provide a concise summary of this email in 3-5 sentences.",
            'sentiment': "Analyze the sentiment of this email. Is it positive, negative, or neutral? Explain why.",
            'action_items': "Extract all action items, tasks, or requests from this email. Format them as a bullet point list.",
            'key_points': "What are the key points or important information in this email? List them in order of importance.",
            'categorize': "Categorize this email (e.g., work, personal, promotional, urgent, informational, etc.) and explain why.",
            'priority': "On a scale of 1-5 (5 being highest), what priority should be assigned to this email? Explain your reasoning.",
            'comprehensive': "Provide a comprehensive analysis of this email including: summary, sentiment, action items, key points, category, and priority level."
        }
    
    def analyze_email(self, email_content, analysis_type='summary'):
        """Analyze an email using AI"""
        if not openai.api_key:
            raise Exception("OpenAI API key is not set. Please check your .env file.")
        
        # Prepare the email content
        email_text = f"Subject: {email_content.get('subject', 'No Subject')}\n"
        email_text += f"From: {email_content.get('from', 'Unknown')}\n"
        email_text += f"Date: {email_content.get('date', 'Unknown')}\n\n"
        email_text += email_content.get('body', '')
        
        # Get the appropriate analysis prompt
        prompt = self.analysis_prompts.get(analysis_type, self.analysis_prompts['summary'])
        
        try:
            # Call OpenAI API for analysis
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes emails and provides insights."},
                    {"role": "user", "content": f"Here is an email:\n\n{email_text}\n\n{prompt}"}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Extract and return the analysis result
            analysis_result = response.choices[0].message.content.strip()
            
            return {
                'analysis_type': analysis_type,
                'result': analysis_result
            }
        except Exception as e:
            raise Exception(f"Error analyzing email: {str(e)}")
