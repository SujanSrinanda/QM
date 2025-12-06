import pytesseract
from PIL import Image
from pypdf import PdfReader

import requests
from requests.exceptions import ConnectionError, ConnectTimeout
import json
import io
import logging

logger = logging.getLogger(__name__)

# NOTE: You might need to set the tesseract path if it's not in your PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_file(uploaded_file):
    """
    Extracts text from a Django UploadedFile object.
    Supports PDF and Common Image formats.
    """
    content_type = uploaded_file.content_type
    filename = uploaded_file.name.lower()
    
    try:
        text = ""
        if 'pdf' in content_type or filename.endswith('.pdf'):
            text = _extract_from_pdf(uploaded_file)
        elif 'image' in content_type or filename.endswith(('.png', '.jpg', '.jpeg')):
            text = _extract_from_image(uploaded_file)
            
        if text:
            return f"Filename: {uploaded_file.name}\n\n{text}"
        else:
            # Fallback if extraction fails but we have filename
            return f"Filename: {uploaded_file.name}\n\n(No readable text found in file. Please infer topic from filename.)"

    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return None

def _extract_from_pdf(file_obj):
    try:
        reader = PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF Extraction Error: {e}")
        return ""

def _extract_from_image(file_obj):
    try:
        image = Image.open(file_obj)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Image Extraction Error: {e}")
        # Fallback message or re-raise depending on requirements
        return ""

def generate_quiz_from_text(text, user_prompt=None, num_questions=5, model="qwen2.5:3b"):
    """
    Generates MCQs using Ollama with the specified model.
    Returns a list of dictionaries.
    Uses a loop to ensure the requested number of questions are generated.
    """
    if not text and not user_prompt:
        return []

    # Construct the context based on available inputs
    context_str = ""
    if text:
        context_str += f"TEXT TO ANALYZE:\n{text[:4000]}\n"
    
    if user_prompt:
        context_str += f"USER INSTRUCTIONS/TOPIC:\n{user_prompt}\n"

    all_questions = []
    attempts = 0
    max_attempts = max(15, num_questions + 10) # Give more attempts for larger requests

    while len(all_questions) < num_questions and attempts < max_attempts:
        attempts += 1
        current_needed = num_questions - len(all_questions)
        
        retry_instruction = ""
        if attempts > 1:
            retry_instruction = "Ensure these questions are DIFFERENT from previous ones."

        prompt = f"""
        You are a Quiz Generator AI. 
        Analyze the provided content and generate EXACTLY {current_needed} multiple-choice questions (MCQs).
        
        CRITICAL INSTRUCTIONS:
        1. **FACTUAL ACCURACY**: Ensure every Question and Answer is FACTUALLY CORRECT. Do not hallucinate statistics. If the content is missing, use verified general knowledge.
        2. **CHAIN OF THOUGHT**: Generate an "explanation" for why the answer is correct to verify your own reasoning.
        3. **UNIQUENESS**: {retry_instruction}
        
        FORMAT YOUR RESPONSE AS A VALID JSON ARRAY ONLY. NO MARKDOWN.
        Each item in the array must have:
        - "question": string
        - "options": dictionary with keys "1", "2", "3", "4"
        - "answer": string (the KEY of the correct option, e.g., "1", "2", "3", or "4")
        - "explanation": string (Brief reason for the answer)

        Content:
        {context_str}
        
        REMINDER: GENERATE {current_needed} QUESTIONS. OUTPUT KEYS FOR ANSWERS.
        """
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("response", "")
            
            # Clean up
            if "```json" in generated_text:
                generated_text = generated_text.split("```json")[1].split("```")[0]
            elif "```" in generated_text:
                generated_text = generated_text.split("```")[1].split("```")[0]
                
            data = json.loads(generated_text)
            
            # Normalize
            if isinstance(data, dict):
                if "questions" in data:
                    data = data["questions"]
                else:
                    data = [data]
            
            if isinstance(data, list):
                for item in data:
                     if "question" in item and "options" in item:
                         # unique check
                         if not any(q.get('question') == item.get('question') for q in all_questions):
                             
                             # --- ANSWER CLEANING LOGIC ---
                             ans = str(item.get("answer", "")).strip()
                             
                             # Handle "Option 1", "Option A"
                             if ans.lower().startswith("option"):
                                 ans = ans.split()[-1]
                             
                             # Handle A, B, C, D
                             map_alpha = {"a": "1", "b": "2", "c": "3", "d": "4"}
                             if ans.lower() in map_alpha:
                                 ans = map_alpha[ans.lower()]
                                 
                             # Normalize to string integer
                             # If explicitly matches a key "1".."4"
                             if ans not in ["1", "2", "3", "4"]:
                                 # Try to fix mapped answer (text match)
                                 match_key = "1" # Default fallback
                                 for k, v in item["options"].items():
                                     if str(v).lower() == ans.lower():
                                         match_key = k
                                         break
                                     # Fuzzy match? (contained in value)
                                     if len(ans) > 5 and ans.lower() in str(v).lower():
                                         match_key = k
                                         break
                                 ans = match_key
                             
                             item["answer"] = ans
                             # -----------------------------
                             
                             all_questions.append(item)
        
        except (ConnectionError, ConnectTimeout) as e:
            logger.error(f"Ollama Connection Error (Attempt {attempts}): {e}")
            logger.error("Is Ollama running? Please start it with 'ollama serve'")
            # Fail fast if the service is down, don't retry 15 times
            break
        except Exception as e:
            logger.error(f"Generation Attempt {attempts} Error: {e}")
    
    return all_questions[:num_questions]

def process_user_intent(user_input, has_file=False):
    """
    Determines if the user wants to generate a quiz or just chat.
    Returns a dictionary with 'type' ('chat' or 'generate') and data.
    """
    text = user_input.lower().strip()
    
    # Keywords that strongly suggest quiz generation
    generation_keywords = ['generate', 'create', 'make', 'quiz', 'questions', 'test', 'exam', 'paper', 'assessment']
    
    if has_file:
        # If a file is uploaded, almost certainly a generation request unless explicitly stated otherwise
        return {'type': 'generate'}
        
    if any(keyword in text for keyword in generation_keywords):
        return {'type': 'generate'}
    
    # Otherwise, treat as casual chat
    response = _get_chat_response(text)
    return {'type': 'chat', 'response': response}

def _get_chat_response(text, model="qwen2.5:3b"):
    """
    Uses Ollama to generate a conversational response.
    """
    prompt = f"""
    You are a friendly and helpful AI assistant for specific QuizMania Application.
    Conversation History: User said "{text}"
    
    Instructions:
    - Answer the user's question or greeting naturally and concisely.
    - If the user asks for general information (e.g., "What is Python?"), provide a brief answer.
    - If strings like "Generate" or "Create" or "Quiz" are NOT present in the user's input, do NOT mention generating a quiz unless asked for help.
    - Keep responses under 50 words if possible.
    """
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "I'm listening.").strip()
    except Exception as e:
        logger.error(f"Chat Generaton Error: {e}")
        return "I am currently offline. Please check my connection."
