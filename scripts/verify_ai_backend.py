
import os
import django
import sys
from pathlib import Path

# Setup Django Environment
sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings') # Assuming QM is the project name
django.setup()

from QuizMania.ai_utils import generate_quiz_from_text

def test_generation():
    print("Testing AI Quiz Generation with Ollama...")
    
    sample_text = """
    Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation.
    Python is dynamically-typed and garbage-collected. It supports multiple programming paradigms, including structured (particularly procedural), object-oriented and functional programming.
    """
    
    print(f"Sending text (len={len(sample_text)}) to model...")
    
    try:
        from QuizMania.ai_utils import process_user_intent

        # Test 1: Intent Classification & Chat Response
        print("\n--- Test 1: Intent & Chat Logic ---")
        intents = [
            ("Hi there", "chat"),
            ("What is the capital of France?", "chat"),
            ("Generate a quiz", "generate"),
        ]
        for text, expected in intents:
            result = process_user_intent(text)
            status = "PASS" if result['type'] == expected else "FAIL"
            print(f"Input: '{text}' -> Intent: {result['type']} [{status}]")
            if result['type'] == 'chat':
                print(f"   Response: {result['response']}")

        # Test 2: Generation (Mock or Real)
        # We can skip full generation if we just want to verify logic wiring
        # But let's keep one real call
        print("\n--- Test 2: User Prompt Generation (Count Check) ---")
        prompt_input = "Generate 3 questions about the Moon."
        questions_prompt = generate_quiz_from_text("", user_prompt=prompt_input, num_questions=3)
        
        if questions_prompt: 
            count = len(questions_prompt)
            print(f"Generated: {count} questions.")
            
            # Inspect first question for Answer Key format
            if count > 0:
                first_q = questions_prompt[0]
                ans = first_q.get('answer')
                print(f"Sample Answer Field: '{ans}'")
                if str(ans) in ["1", "2", "3", "4"]:
                     print("SUCCESS: Answer is a valid key.")
                else:
                     print(f"WARNING: Answer '{ans}' might be text, not a key.")

            if count == 3:
                print("SUCCESS: Count matches requested (3).")
            else:
                print(f"WARNING: Count mismatch (Wanted 3, Got {count}). Model might be inconsistent.")
        else: print("FAILURE: No questions from prompt.")

    except Exception as e:
        print(f"\nERROR: Verification failed with exception: {e}")

if __name__ == "__main__":
    test_generation()
