import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings')
django.setup()

from QuizMania.models import Quiz, QuizTaker, User

CODE = 'G58X75'

try:
    quiz = Quiz.objects.get(code=CODE)
    print(f"Quiz Found: {quiz.title} (Owner: {quiz.owner.username})")
    
    takers = QuizTaker.objects.filter(quiz=quiz)
    print(f"Active QuizTakers: {takers.count()}")
    for t in takers:
        print(f" - User: {t.user.username}, Alias: {t.alias}, Score: {t.score}")
        
    if takers.count() > 0:
        print("Records exist! Attempting force delete...")
        count, _ = takers.delete()
        print(f"Deleted {count} records. User should be able to join now.")
    else:
        print("No active records found. Join error must be logical?")

except Quiz.DoesNotExist:
    print(f"Quiz {CODE} not found.")
