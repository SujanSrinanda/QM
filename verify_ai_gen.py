import logging
import sys
import os
import django

# Setup Django environment just in case, though ai_utils looks mostly standalone
# It might verify headers or usage later.
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings')
django.setup()

from QuizMania.ai_utils import generate_quiz_from_text

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("QuizMania.ai_utils")
logger.setLevel(logging.INFO)

print("--- Starting AI Generation Verification ---")
user_prompt = "Generate 3 random trivia questions about space."
print(f"Prompt: {user_prompt}")

try:
    questions = generate_quiz_from_text(
        text="",
        user_prompt=user_prompt,
        num_questions=3,
        model="qwen2.5:3b"
    )

    print(f"\nGeneraton Combined Result: {len(questions)} questions.")
    for i, q in enumerate(questions):
        print(f"[{i+1}] {q.get('question')}")
        print(f"    Options: {q.get('options')}")
        print(f"    Answer: {q.get('answer')}")
        print(f"    Explanation: {q.get('explanation')}")

    if len(questions) == 3:
        print("\nSUCCESS: Verification Passed.")
    else:
        print(f"\nFAILURE: Expected 3 questions, got {len(questions)}.")

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
