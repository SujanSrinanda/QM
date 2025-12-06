
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings')
django.setup()

from QuizMania.models import Quiz
from django.contrib.auth.models import User

def inspect():
    quiz_code = 'ARTIJY'
    try:
        quiz = Quiz.objects.get(code=quiz_code)
        print(f"Quiz found: {quiz.title} (Code: {quiz.code})")
        print(f"Owner: {quiz.owner.username} (ID: {quiz.owner.id})")
        
        print("\nAll Users:")
        for u in User.objects.all():
            print(f"- {u.username} (ID: {u.id})")
            
    except Quiz.DoesNotExist:
        print(f"Quiz with code {quiz_code} DOES NOT EXIST.")
        print("\nExisting Quizzes:")
        for q in Quiz.objects.all():
            print(f"- {q.title} ({q.code}) Owner: {q.owner.username}")

if __name__ == "__main__":
    inspect()
