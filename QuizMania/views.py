from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Quiz, Question, Choice, QuizTaker
from django.contrib.auth.models import User
from django.http import JsonResponse

def home(request):
    return render(request, 'QuizMania/home.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'QuizMania/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'QuizMania/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def ai_quiz_generator(request):
    mcqs = None
    if request.method == 'POST':
        # Placeholder for AI generation logic
        # In a real scenario, you would process the uploaded 'document' and 'num_questions'
        # using an AI model to generate MCQs.
        # For demonstration, I'll create some dummy MCQs.
        
        try:
            num_questions = int(request.POST.get('num_questions', 1))
        except (ValueError, TypeError):
            num_questions = 1
        uploaded_document = request.FILES.get('document')

        # Dummy MCQ generation
        mcqs = []
        for i in range(num_questions):
            mcqs.append({
                'question': f'Dummy Question {i+1} from AI Mode?',
                'options': {
                    '1': 'Option A',
                    '2': 'Option B',
                    '3': 'Option C',
                    '4': 'Option D',
                },
                'answer': 'Option A' # Dummy correct answer
            })
        
        # If the form action is to save the generated questions
        if 'title' in request.POST:
            quiz_title = request.POST.get('title')
            quiz = Quiz.objects.create(title=quiz_title, owner=request.user)

            for j in range(num_questions):
                question_text = request.POST.get(f'question_text_{j+1}')
                try:
                    marks = int(request.POST.get(f'marks_{j+1}', 10))
                    duration = int(request.POST.get(f'duration_{j+1}', 5))
                except (ValueError, TypeError):
                    marks = 10
                    duration = 5
                
                question = Question.objects.create(quiz=quiz, text=question_text, marks=marks, duration=duration)

                for k in range(1, 5): # Assuming 4 options
                    option_text = request.POST.get(f'option_{k}_{j+1}')
                    is_correct = (request.POST.get(f'correct_option_{j+1}') == str(k))
                    Choice.objects.create(question=question, text=option_text, is_correct=is_correct)
            
            return redirect('quiz_master_dashboard', quiz_code=quiz.code)


    return render(request, 'QuizMania/ai_quiz_generator.html', {'mcqs': mcqs})

@login_required
def start_session(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        quiz = Quiz.objects.create(title=title, owner=request.user)

        # Process dynamically added questions
        question_keys = [key for key in request.POST if key.startswith('question_text_')]
        
        # Extract unique question IDs from the keys
        question_ids = []
        for key in question_keys:
            try:
                q_id = int(key.split('_')[-1])
                question_ids.append(q_id)
            except (ValueError, IndexError):
                continue
        question_ids = sorted(list(set(question_ids)))

        for q_id in question_ids:
            question_text = request.POST.get(f'question_text_{q_id}')
            
            try:
                marks = int(request.POST.get(f'marks_{q_id}', 10))
                duration = int(request.POST.get(f'duration_{q_id}', 5))
            except (ValueError, TypeError):
                marks = 10
                duration = 5

            question = Question.objects.create(quiz=quiz, text=question_text, marks=marks, duration=duration)

            # Process options for this question
            for i in range(1, 5): # Assuming 4 options
                option_text = request.POST.get(f'option_{i}_{q_id}')
                is_correct = request.POST.get(f'correct_option_{q_id}') == str(i)
                Choice.objects.create(question=question, text=option_text, is_correct=is_correct)

        return redirect('quiz_master_dashboard', quiz_code=quiz.code)
    
    return render(request, 'QuizMania/start_session.html')

@login_required
def quiz_master_dashboard(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code, owner=request.user)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz)
    return render(request, 'QuizMania/quiz_master_dashboard.html', {'quiz': quiz, 'quiz_takers': quiz_takers})

def join_session(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().replace('\u201c', '').replace('\u201d', '')
        username = request.POST.get('username')
        
        if not username:
             return render(request, 'QuizMania/join_session.html', {'error': 'Username is required'})

        try:
            quiz = Quiz.objects.get(code=code)
            
            if request.user.is_authenticated:
                if request.user.username == username:
                    user = request.user
                else:
                    # User wants to join as someone else
                    logout(request)
                    # Proceed to create/get new user logic below
                    if User.objects.filter(username=username).exists():
                         return render(request, 'QuizMania/join_session.html', {'error': 'Username taken. Please choose another or login.'})
                    user = User.objects.create_user(username=username)
                    login(request, user)
            else:
                # Check if username is taken
                if User.objects.filter(username=username).exists():
                     return render(request, 'QuizMania/join_session.html', {'error': 'Username taken. Please choose another or login.'})
                
                # Create new guest user
                user = User.objects.create_user(username=username)
                login(request, user)

            quiz_taker, created = QuizTaker.objects.get_or_create(quiz=quiz, user=user)
            return redirect('quiz_view', quiz_code=quiz.code, username=user.username)
        except (Quiz.DoesNotExist, ValueError):
            return render(request, 'QuizMania/join_session.html', {'error': 'Invalid quiz code'})
    return render(request, 'QuizMania/join_session.html')

@login_required
def quiz_view(request, quiz_code, username):
    # Ensure the logged-in user matches the requested username
    if request.user.username != username:
         return redirect('home') # Or show a 403 Forbidden page

    quiz = get_object_or_404(Quiz, code=quiz_code)
    user = request.user
    if request.method == 'POST':
        score = 0
        for question in quiz.questions.all():
            selected_choice_id = request.POST.get(f'question_{question.id}')
            if selected_choice_id:
                # Validate that the choice actually belongs to this question
                choice = Choice.objects.filter(id=selected_choice_id, question=question).first()
                if choice and choice.is_correct:
                    score += question.marks
        quiz_taker = get_object_or_404(QuizTaker, quiz=quiz, user=user)
        quiz_taker.score = score
        quiz_taker.save()
        return redirect('results_view', quiz_code=quiz.code)
    return render(request, 'QuizMania/quiz_view.html', {'quiz': quiz, 'user': user})

def results_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz).order_by('-score')[:5]
    return render(request, 'QuizMania/results.html', {'quiz': quiz, 'quiz_takers': quiz_takers})

def live_count(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    count = QuizTaker.objects.filter(quiz=quiz).count()
    return JsonResponse({'live_count': count})

def live_scoreboard(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz).order_by('-score')
    data = [{'username': taker.user.username, 'score': taker.score} for taker in quiz_takers]
    return JsonResponse(data, safe=False)

def live_participants_list(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz)
    data = [{'username': taker.user.username} for taker in quiz_takers]
    return JsonResponse(data, safe=False)


@login_required
def live_participants_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code, owner=request.user)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz)
    return render(request, 'QuizMania/live_participants.html', {'quiz': quiz, 'quiz_takers': quiz_takers})

@login_required
def live_scoreboard_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code, owner=request.user)
    return render(request, 'QuizMania/live_scoreboard.html', {'quiz': quiz})