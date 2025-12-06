from django.db import models
from django.contrib.auth.models import User
import random
import string

def generate_unique_code():
    length = 6
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if Quiz.objects.filter(code=code).count() == 0:
            break
    return code

class Quiz(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=6, default=generate_unique_code, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    marks = models.IntegerField(default=1)
    duration = models.IntegerField(default=5) # Duration in seconds

    def __str__(self):
        return self.text

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class QuizTaker(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    alias = models.CharField(max_length=255, default="Guest")
    score = models.IntegerField(default=0)
    
    def __str__(self):
        return self.user.username

class QuizHistory(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='history')
    player_name = models.CharField(max_length=255)
    score = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player_name} - {self.quiz.title}"