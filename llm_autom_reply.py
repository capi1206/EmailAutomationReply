# Configuration and imports
import os
import re
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Sample email dataset
sample_emails = [
    {
        "id": "001",
        "from": "angry.customer@example.com",
        "subject": "Broken product received",
        "body": "I received my order #12345 yesterday but it arrived completely damaged. This is unacceptable and I demand a refund immediately. This is the worst customer service I've experienced.",
        "timestamp": "2024-03-15T10:30:00Z"
    },
    {
        "id": "002",
        "from": "curious.shopper@example.com",
        "subject": "Question about product specifications",
        "body": "Hi, I'm interested in buying your premium package but I couldn't find information about whether it's compatible with Mac OS. Could you please clarify this? Thanks!",
        "timestamp": "2024-03-15T11:45:00Z"
    },
    {
        "id": "003",
        "from": "happy.user@example.com",
        "subject": "Amazing customer support",
        "body": "I just wanted to say thank you for the excellent support I received from Sarah on your team. She went above and beyond to help resolve my issue. Keep up the great work!",
        "timestamp": "2024-03-15T13:15:00Z"
    },
    {
        "id": "004",
        "from": "tech.user@example.com",
        "subject": "Need help with installation",
        "body": "I've been trying to install the software for the past hour but keep getting error code 5123. I've already tried restarting my computer and clearing the cache. Please help!",
        "timestamp": "2024-03-15T14:20:00Z"
    },
    {
        "id": "005",
        "from": "business.client@example.com",
        "subject": "Partnership opportunity",
        "body": "Our company is interested in exploring potential partnership opportunities with your organization. Would it be possible to schedule a call next week to discuss this further?",
        "timestamp": "2024-03-15T15:00:00Z"
    }
]


class EmailProcessor:
    def __init__(self):
        """Initialize the email processor with OpenAI API key."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Define valid categories
        self.valid_categories = {
            "complaint", "inquiry", "feedback",
            "support_request", "other"
        }

    def classify_email(self, email: Dict) -> Optional[str]:
        """
        Classify an email using LLM.
        Returns the classification category or None if classification fails.
        """
        prompt = f"""You're a helpful ai assistant with the task of classifying an email.
        For the email with body: {email["body"]}. And subject: {email["subject"]}. Provide as an answer
        which of the following categories is the best fit, categories : [
            complaint
            inquiry
            feedback
            support_request
            other
        ] please reply only with one of the mentioned categories.
        """
        try:
            completions = self.client.chat.completions.create(messages = [
                {"role": "user",
                    "content": prompt,}],
                    model="gpt-3.5-turbo",
                    max_tokens=10)
            classification = completions.choices[0].message.content.strip().lower()
            if classification in self.valid_categories:
                return classification
            else:
                return "other"
        except Exception:
            logger.info(f"Error classifying email with id {email["id"]}")
            return None    
            

    def generate_response(self, email: Dict, classification: str) -> Optional[str]:
        """
        Generate an automated response based on email classification, 
        returns None if generation fails. 
        
        """
        dict_prompt = {
            "complaint": "Please give a considerate reply appologizing for the caused inconvenience and providing a way to fix the usser's issues if possible.",
            "inquiry": "Please reply with a thoughtful answer to the user's inquiry giving all necessary information.",
            "feedback": "Please thank the user for his valuable feedback. And tell that the necessary changes to accomodate for this will be carried out.",
            "support_request": "Please provide the user with helpful and clear instructions on how to troubleshot the issue.",
            "other": "Please answer thoughtfuly to the user providing a general answer to his inquiry."
        }
        prompt = f"""You are a helpful ai assistant and your task is to reply to the following email that has 
        the body :{email["body"]}. {dict_prompt[classification]}.
        """
        
        try:
            completions = self.client.chat.completions.create(
                model ="gpt-3.5-turbo",
                messages=[
                    {"role": "user",
                    "content" : prompt }],
                max_tokens= 100
            ) 
            response = completions.choices[0].message.content.strip()
            return response
        except Exception:
            logger.info(f"Error generating response to email with id {email["id"]}")
            return None


class EmailAutomationSystem:
    def __init__(self, processor: EmailProcessor):
        """Initialize the automation system with an EmailProcessor."""
        self.processor = processor
        
        
    def _validate_email(self, email :Dict):
        """Checks the right format of the email
        returns bool
        """
        mandatory_keys ={ "id",
            "from",
            "subject",
            "body", "timestamp"}
        #checks for the presence of the necessary keys in email 
        if not mandatory_keys.issubset(email.keys()):
            logger.info(f"email with id {email.get("id", "Uknown")} has incorrect format.")
            return False
    
        #check right format of the email address
        email_ex = re.compile(r"[a-zA-Z0-9.*%±]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}")
        if not email_ex.match(email["from"]):
            logger.info(f"email with id {email.get("id", "Uknown")} has incorrect 'from' address format.")
            return False
    
        #check for right timestamp format
        try:
            datetime.strptime(email["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
            return True
        except Exception:
            logger.info(f"email with id {email.get("id", "Uknown")} has incorrect timestamp format.")
            return False    

    def _send_response(self, email_id: str, response: str):
        """Mock function to simulate sending a response."""
        logger.info(f"Sending complaint response for email {email_id}")
        # In real implementation: integrate with email service
        
    def process_email(self, email: Dict) -> Dict:
        """
        Process a single email through the complete pipeline.
        Returns a dictionary with the processing results.
        
        """
        #check for email validity (format)
        if not self._validate_email(email):
            return { "email_id" : email.get("id", "Uknown") , 
                    "success" : False, 
                    "classification" : "Email in invalid format.", 
                    "response_sent" : None}
            
        #find the classification of the email
        classification = self.processor.classify_email(email) 
        if not classification:
            return { "email_id" : email["id"] , 
                    "success" : False, 
                    "classification" : "Email classification error.", 
                    "response_sent" : None}   
            
        #generate a response for the email accordingly
        response = self.processor.generate_response(email, classification)
        if not response: 
            return { "email_id" : email["id"] , 
                    "success" : False, 
                    "classification" : "Response generation error.", 
                    "response_sent" : None}     
            
        self._send_response(email["id"], response)
        
        return { "email_id" : email["id"], 
                "success" : True, 
                "classification" :classification, "response_sent" : response}
    




def run_demonstration():
    """Run a demonstration of the complete system."""
    # Initialize the system
    processor = EmailProcessor()
    automation_system = EmailAutomationSystem(processor)

    # Process all sample emails
    results = []
    for email in sample_emails:
        logger.info(f"\nProcessing email {email['id']}...")
        result = automation_system.process_email(email)
        results.append(result)

    # Create a summary DataFrame
    df = pd.DataFrame(results)
    print("\nProcessing Summary:")
    print(df[["email_id", "success", "classification", "response_sent"]])

    return df



# Example usage:
if __name__ == "__main__":
    results_df = run_demonstration()
    