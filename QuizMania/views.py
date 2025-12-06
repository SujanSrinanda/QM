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

from .ai_utils import extract_text_from_file, generate_quiz_from_text, process_user_intent

from django.template.loader import render_to_string

@login_required
def ai_quiz_generator(request):
    if request.method == 'POST':
        try:
            num_questions = int(request.POST.get('num_questions', 5))
            if not (0 < num_questions <= 200):
                num_questions = 5
        except (ValueError, TypeError):
            num_questions = 5
        
        user_input = request.POST.get('user_input', '').strip()
        uploaded_document = request.FILES.get('document')
        
        # Check if we are in the generation phase (file uploaded or user input provided)
        # and NOT in the saving phase (which is identified by 'title')
        if 'title' not in request.POST and (uploaded_document or user_input):
            
            # Determine Intent
            has_file = bool(uploaded_document)
            intent = process_user_intent(user_input, has_file)
            
            if intent['type'] == 'chat':
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    html = render_to_string('QuizMania/partials/ai_chat_bubble_partial.html', {'response': intent['response']}, request=request)
                    return JsonResponse({'html': html})
            
            else: # GENERATE
                # 1. Prioritize explicitly submitted num_questions (from the box)
                # Note: We already grabbed num_questions at the top of the view.
                # But let's check if the user prompt has a specific override desire?
                # Actually, usually the box is authoritative if present.
                # But if the box is default (5) and prompt says "10", prompt should win.
                # However, logic at top sets num_questions=5 on error.
                
                # Let's verify what we have.
                print(f"DEBUG: Initial Num Questions: {num_questions}", flush=True)

                import re
                found_numbers = re.findall(r'\b\d+\b', user_input)
                if found_numbers:
                    try:
                        parsed_num = int(found_numbers[0])
                        # If prompt has a number, and it differs from default 5, let's use it?
                        # Or if it differs from the box? 
                        # User typed "Generate 2" but box says "10". 
                        # Let's trust the Prompt as "Process User Intent" usually implies following instructions.
                        if 0 < parsed_num <= 200:
                            num_questions = parsed_num
                            print(f"DEBUG: Overriding with Prompt Num: {num_questions}", flush=True)
                    except ValueError:
                        pass
                
                print(f"DEBUG: Final User Input: '{user_input}' | Num Questions: {num_questions}", flush=True)
                
                text = ""
                if uploaded_document:
                    text = extract_text_from_file(uploaded_document)
                    if not text:
                         print("ERROR: Failed to extract text from file", flush=True)
                    else:
                         print(f"DEBUG: Extracted Text Length: {len(text)}", flush=True)
                
                # Generate Questions
                mcqs = generate_quiz_from_text(text, user_prompt=user_input, num_questions=num_questions)
                print(f"DEBUG: Generated MCQs Count: {len(mcqs)}", flush=True)
                
                # AJAX Response for Chat Interface
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    html = render_to_string('QuizMania/partials/ai_response_partial.html', {'mcqs': mcqs}, request=request)
                    return JsonResponse({'html': html})
        
        # Check if we are in the saving phase (title present) - Legacy handling if any
        elif 'title' in request.POST:
             # This block might not be reached directly anymore for saving via chat, 
             # as we redirect to review page, but keeping for safety.
             pass

    return render(request, 'QuizMania/ai_quiz_generator.html')

@login_required
def review_generated_quiz(request):
    if request.method == 'POST':
        try:
            try:
                num_questions = int(request.POST.get('num_questions', 0))
            except (ValueError, TypeError):
                 num_questions = 0

            title = request.POST.get('title', 'Generated Quiz')
            questions = []

            for i in range(1, num_questions + 1):
                q_text = request.POST.get(f'question_text_{i}')
                answer = request.POST.get(f'answer_{i}') # Suggested answer explanation or text
                
                options = {}
                correct_option = None
                
                # Let's reconstruct standard options 1-4
                for k in range(1, 5):
                    opt_val = request.POST.get(f'option_{k}_{i}')
                    if opt_val:
                        options[k] = opt_val
                
                # Cast answer to int to match option keys
                valid_answer = None
                try:
                    if answer:
                         valid_answer = int(answer)
                except (ValueError, TypeError):
                    pass

                # Let's just pass the data we have.
                questions.append({
                    'id': i,
                    'text': q_text,
                    'options': options,
                    'correct_option': valid_answer, 
                    'answer': answer # Keep original for debug
                })

            return render(request, 'QuizMania/review_quiz.html', {'title': title, 'questions': questions})
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ERROR in review_generated_quiz: {e}")
            return render(request, 'QuizMania/review_quiz.html', {'title': "Error Loading Quiz", 'questions': []})
    
    return redirect('ai_quiz_generator')


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