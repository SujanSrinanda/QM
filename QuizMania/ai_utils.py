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
    max_attempts = max(10, num_questions + 5) 

    while len(all_questions) < num_questions and attempts < max_attempts:
        attempts += 1
        current_needed = num_questions - len(all_questions)
        
        # Determine batch size to avoid overwhelming small model
        batch_size = min(5, current_needed) 
        
        retry_instruction = ""
        if attempts > 1:
            retry_instruction = "Ensure these questions are DIFFERENT from previous ones."

        prompt = f"""
        You are a Quiz Generator AI. 
        Analyze the provided content and generate EXACTLY {batch_size} multiple-choice questions (MCQs).
        
        CRITICAL INSTRUCTIONS:
        1. **FACTUAL ACCURACY**: Ensure every Question and Answer is FACTUALLY CORRECT.
        2. **FORMAT**: RESPOND ONLY WITH A VALID JSON ARRAY. No introductory text. No markdown formatting.
        
        REQUIRED JSON STRUCTURE EXAMPLE:
        [
            {{
                "question": "What is the output of print(2+2)?",
                "options": {{
                    "1": "3",
                    "2": "4",
                    "3": "5",
                    "4": "22"
                }},
                "answer": "2",
                "explanation": "The addition operator adds two numbers."
            }}
        ]
        
        GENERATE {batch_size} QUESTIONS NOW. CONTENT:
        {context_str}
        {retry_instruction}
        """
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json", # Enforce JSON mode if supported by Ollama version
            "options": {
                "temperature": 0.7 # Slight creativity but kept focused
            }
        }

        try:
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=90)
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("response", "")
            
            # --- ROBUST PARSING LGOIC ---
            import re
            data = None
            
            # 1. Try Direct JSON Load
            try:
                data = json.loads(generated_text)
            except json.JSONDecodeError:
                # 2. Try identifying JSON Array via Regex
                match = re.search(r'\[.*\]', generated_text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except:
                        pass
            
            if not data:
                # 3. Last ditch: Try to find incomplete json or weird formatting?
                # Usually regex handles the markdown block case too if it contains [ ].
                logger.warning(f"Failed to parse JSON for attempt {attempts}. Text snippet: {generated_text[:100]}...")
                continue # Retry loop

            # Normalize
            if isinstance(data, dict):
                if "questions" in data:
                    data = data["questions"]
                else:
                    data = [data]
            
            if isinstance(data, list):
                for item in data:
                     # VALIDATION & CLEANING
                     if "question" in item and "options" in item and "answer" in item:
                         # --- QUESTION CLEANING ---
                         q_text = str(item.get("question", "")).strip()
                         # Fix common artifact: "? ng code" -> "code" or remove leading special chars
                         # Remove leading non-alphanumeric (except basic punctuation if reasonable, but usually questions start with letters)
                         # Regex: remove leading non-word chars except open parens (in case of "(a)...")
                         import re
                         # Clean garbage like "? ng " which might be a hallucinated "Following" or similar
                         q_text = re.sub(r'^[\?\.\-\s]+', '', q_text) 
                         # Fix "ng code" if it's a common truncation of "Following code"
                         q_text = q_text.replace("ng code", "following code")
                         
                         item["question"] = q_text
                         
                         # STRICT VALIDATION
                         # 1. Length check
                         if len(q_text) < 10:
                             continue
                         # 2. Start character check (should look like a sentence)
                         if not q_text[0].isalnum() and q_text[0] not in ['"', "'", '(']:
                             continue

                         # Check that options is a dict and has enough items
                         options = item.get("options")
                         if isinstance(options, dict) and len(options) >= 2:
                             # unique check
                             if not any(q.get('question') == item.get('question') for q in all_questions):
                                 
                                 # --- ANSWER CLEANING ---
                                 ans = str(item.get("answer", "")).strip()
                                 # Handle A, B, C, D maps
                                 map_alpha = {"a": "1", "b": "2", "c": "3", "d": "4"}
                                 if ans.lower() in map_alpha:
                                     ans = map_alpha[ans.lower()]
                                     
                                 # Fallback: if answer is the value text, find the key
                                 if ans not in ["1", "2", "3", "4"]:
                                    for k, v in options.items():
                                         if str(v).lower() == ans.lower():
                                             ans = k
                                             break
                                 
                                 item["answer"] = ans
                                 # -----------------------
                                 
                                 all_questions.append(item)
        
        except (ConnectionError, ConnectTimeout) as e:
            logger.error(f"Ollama Connection Error (Attempt {attempts}): {e}")
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
        print("DEBUG: Sending request to Ollama...", flush=True)
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "I'm listening.").strip()
    except Exception as e:
        logger.error(f"Chat Generaton Error: {e}")
        return "I am currently offline. Please check my connection."
