
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings')
django.setup()

from django.urls import resolve, reverse
from django.contrib.auth.models import User
from QuizMania.models import Quiz
from django.test import RequestFactory
from QuizMania.views import live_participants_view
from django.http import Http404

def test_url():
    url = '/quiz/ARTIJY/live_participants/'
    print(f"Testing URL: {url}")
    
    try:
        resolved = resolve(url)
        print(f"Resolved to view: {resolved.func.__name__}")
        print(f"URL Name: {resolved.url_name}")
        print(f"Kwargs: {resolved.kwargs}")
    except Exception as e:
        print(f"Failed to resolve URL: {e}")
        return

    # Create dummy user and quiz
    username = 'test_owner'
    password = 'password123'
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, password=password)
    else:
        user = User.objects.get(username=username)
        
    quiz_code = 'ARTIJY'
    if not Quiz.objects.filter(code=quiz_code).exists():
        quiz = Quiz.objects.create(title="Test Quiz", owner=user, code=quiz_code)
        print(f"Created quiz {quiz_code} for user {username}")
    else:
        quiz = Quiz.objects.get(code=quiz_code)
        # Ensure owner is correct
        quiz.owner = user
        quiz.save()
        print(f"Using existing quiz {quiz_code}, updated owner to {username}")

    # Test the view directly
    factory = RequestFactory()
    request = factory.get(url)
    request.user = user # Simulate logged in user
    
    print("\nCalling view live_participants_view...")
    try:
        response = live_participants_view(request, quiz_code=quiz_code)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
             print("SUCCESS: View returned 200 OK")
        else:
             print("FAILURE: View returned non-200")
    except Http404:
        print("got Http404 exception!")
    except Exception as e:
        print(f"View raised exception: {e}")

    # Test with wrong user
    other_user = User.objects.create_user(username='intruder', password='password')
    request.user = other_user
    print("\nCalling view with WRONG user...")
    try:
        response = live_participants_view(request, quiz_code=quiz_code)
        print(f"Response status: {response.status_code}")
    except Http404:
        print("got Http404 exception as expected")
    except Exception as e:
        print(f"View raised exception: {e}")
        
    # Clean up
    quiz.delete()
    user.delete()
    other_user.delete()

if __name__ == "__main__":
    test_url()
