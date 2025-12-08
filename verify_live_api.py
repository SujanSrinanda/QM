import os
import django
import json
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QM.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from QuizMania.models import Quiz, QuizTaker

# 1. Setup Data
print("--- Setting up Test Data ---")
username = "TestUser_LiveFeed"
if not User.objects.filter(username=username).exists():
    user = User.objects.create_user(username=username, password="password")
else:
    user = User.objects.get(username=username)

quiz_code = "TEST_LIVE_CODE"
if not Quiz.objects.filter(code=quiz_code).exists():
    quiz = Quiz.objects.create(title="Test Quiz", owner=user, code=quiz_code)
else:
    quiz = Quiz.objects.get(code=quiz_code)

# Add user as taker
if not QuizTaker.objects.filter(quiz=quiz, user=user).exists():
    QuizTaker.objects.create(quiz=quiz, user=user)

print(f"Quiz created: {quiz.title} ({quiz.code})")
print(f"User added as taker: {user.username}")

# 2. Test API
print("\n--- Testing API Endpoint ---")
client = Client()
url = f"/api/quiz/{quiz_code}/live_participants_list/"
print(f"GET {url}")

try:
    response = client.get(url, HTTP_HOST='localhost')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        content = response.json()
        print(f"Response Content: {content}")
        
        # Verify content
        usernames = [item['username'] for item in content]
        if username in usernames:
            print("SUCCESS: User found in response.")
        else:
            print("FAILURE: User NOT found in response.")
    else:
        print(f"FAILURE: Unexpected status code. Response: {response.content}")

except Exception as e:
    print(f"CRITICAL ERROR calling API: {e}")
