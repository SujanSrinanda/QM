
import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client, RequestFactory
from QuizMania.models import Quiz, Question, Choice, QuizTaker
from QuizMania.views import quiz_view

def test_quiz_scoring():
    print("Setting up test data...")
    user, _ = User.objects.get_or_create(username='testuser_repro')
    owner, _ = User.objects.get_or_create(username='owner_repro')
    
    quiz = Quiz.objects.create(owner=owner, title="Test Quiz Repro")
    print(f"Created Quiz: {quiz.code}")
    
    q1 = Question.objects.create(quiz=quiz, text="Q1", marks=10)
    c1_correct = Choice.objects.create(question=q1, text="Correct", is_correct=True)
    c1_wrong = Choice.objects.create(question=q1, text="Wrong", is_correct=False)
    
    qt, created = QuizTaker.objects.get_or_create(quiz=quiz, user=user)
    print(f"QuizTaker created: {created}, QT ID: {qt.id}")

    data = {
        f'question_{q1.id}': c1_correct.id,
    }
    
    factory = RequestFactory()
    request = factory.post(f'/quiz/{quiz.code}/{user.username}/', data)
    request.user = user
    
    print("Calling quiz_view...")
    quiz_view(request, quiz.code, user.username)
    
    qt.refresh_from_db()
    print(f"Final Score: {qt.score}")
    
    if qt.score == 10:
        print("PASS")
    else:
        print("FAIL")

    # TEST CASE: Cross-Question Injection
    print("\nTest Case: Cross-Question Injection")
    # Reset score
    qt.score = 0
    qt.save()
    
    # Try to answer Q1 using Q2's correct choice ID? 
    # Actually, we need another question for this test.
    q2 = Question.objects.create(quiz=quiz, text="Q2", marks=20)
    c2_correct = Choice.objects.create(question=q2, text="Correct Q2", is_correct=True)
    
    # Submitting c2_correct (from Q2) as answer for Q1
    data_injection = {
        f'question_{q1.id}': c2_correct.id,
    }
    
    request = factory.post(f'/quiz/{quiz.code}/{user.username}/', data_injection)
    request.user = user
    quiz_view(request, quiz.code, user.username)
    
    qt.refresh_from_db()
    print(f"Injection Score: {qt.score}")
    
    # Expectation: Should be 0 because c2_correct does not belong to Q1.
    # Current behavior might be +10 (if it checks choice.is_correct) or +20?
    # Logic is: score += question.marks (10). 
    # If choice is just retrieved by ID, it is valid and correct.
    
    if qt.score == 0:
        print("PASS: Cross-question rejected.")
    else:
        print(f"FAIL: Cross-question accepted (Score: {qt.score}).")

if __name__ == '__main__':
    test_quiz_scoring()
