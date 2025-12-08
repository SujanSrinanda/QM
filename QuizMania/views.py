from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Quiz, Question, Choice, QuizTaker, QuizHistory, UserResponse
from django.contrib.auth.models import User

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
            print(f"DEBUG: Processing AI Request - Input: '{user_input}', File: {uploaded_document}", flush=True)
            
            # Determine Intent
            has_file = bool(uploaded_document)
            intent = process_user_intent(user_input, has_file)
            print(f"DEBUG: Intent Detected: {intent}", flush=True)
            
            if intent['type'] == 'chat':
                print(f"DEBUG: Chat Intent. AJAX Header present: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}", flush=True)
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
                found_numbers = re.findall(r'\\b\\d+\\b', user_input)
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

            question = Question.objects.create(
                quiz=quiz, 
                text=question_text, 
                marks=marks, 
                duration=duration,
                explanation=request.POST.get(f'answer_{q_id}', '') # Use 'answer' field as explanation
            )

            # Process options for this question
            for i in range(1, 5): # Assuming 4 options
                option_text = request.POST.get(f'option_{i}_{q_id}')
                if option_text and option_text.strip():
                    is_correct = request.POST.get(f'correct_option_{q_id}') == str(i)
                    Choice.objects.create(question=question, text=option_text, is_correct=is_correct)

        return redirect('quiz_master_dashboard', quiz_code=quiz.code)
    
    return render(request, 'QuizMania/start_session.html')

@login_required
def quiz_master_dashboard(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    
    # Security Check: Only owner can view dashboard
    if request.user != quiz.owner:
        return redirect('home')

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
            
            # Authenticated User Logic (Registered Students or Owner)
            if request.user.is_authenticated:
                quiz_taker, created = QuizTaker.objects.get_or_create(quiz=quiz, user=request.user, defaults={'alias': username})
            else:
                # GUEST LOGIC (No User Account Created)
                # Check for alias collision in this specific quiz (Prevent Duplicates if possible, or just allow common names?)
                # Decision: Prevent exact duplicate in same active session to avoid confusion on scoreboard.
                if QuizTaker.objects.filter(quiz=quiz, alias=username).exists():
                     return render(request, 'QuizMania/join_session.html', {'error': f"The name '{username}' is already in this quiz. Please choose another."})
                
                # Create guest taker (User is NULL)
                quiz_taker = QuizTaker.objects.create(quiz=quiz, user=None, alias=username)
                
                # Store ID in session to identify this guest subsequently
                request.session['quiz_taker_id'] = quiz_taker.id
                
            return redirect('quiz_view', quiz_code=quiz.code, username=quiz_taker.alias)
        except (Quiz.DoesNotExist, ValueError):
            return render(request, 'QuizMania/join_session.html', {'error': 'Invalid quiz code'})
    return render(request, 'QuizMania/join_session.html')

# Removed @login_required to allow Guests
def quiz_view(request, quiz_code, username):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    
    quiz_taker = None

    # 1. Try Authenticated User (Registered or Owner)
    if request.user.is_authenticated:
        try:
            quiz_taker = QuizTaker.objects.get(quiz=quiz, user=request.user)
        except QuizTaker.DoesNotExist:
            # Owner previewing?
            if request.user == quiz.owner:
                 pass 
    
    # 2. Try Guest Session
    if not quiz_taker:
        qt_id = request.session.get('quiz_taker_id')
        if qt_id:
            try:
                found_taker = QuizTaker.objects.get(id=qt_id, quiz=quiz)
                # Security Check: Ensure alias matches URL to prevent spoofing
                if found_taker.alias == username:
                    quiz_taker = found_taker
            except QuizTaker.DoesNotExist:
                pass
    
    # 3. Access Denied if no valid taker found
    if not quiz_taker:
        # Allow Owner to view empty template for preview
        if request.user.is_authenticated and request.user == quiz.owner:
             pass 
        else:
             return redirect('join_session')

    if request.method == 'POST':
        if not quiz_taker:
             return redirect('join_session')

        score = 0
        print(f"DEBUG: Processing Quiz Submission for {quiz_taker.alias} - Quiz {quiz.code}", flush=True)
        # Clear previous responses for this attempt
        UserResponse.objects.filter(quiz_taker=quiz_taker).delete()
        
        for question in quiz.questions.all():
            selected_choice_id = request.POST.get(f'question_{question.id}')
            print(f"DEBUG: Q{question.id} ({question.text[:10]}...) - Selected ID: {selected_choice_id}", flush=True)
            
            if selected_choice_id:
                # Validate that the choice actually belongs to this question
                choice = Choice.objects.filter(id=selected_choice_id, question=question).first()
                if choice:
                    # Save response
                    UserResponse.objects.create(
                        quiz_taker=quiz_taker,
                        question=question,
                        selected_choice=choice
                    )
                    # print(f"DEBUG: Saved Response for Q{question.id}", flush=True)
                    
                    if choice.is_correct:
                        score += question.marks
        
        quiz_taker.score = score
        quiz_taker.save()
        return redirect('results_view', quiz_code=quiz.code)
    
    questions = quiz.questions.all()
    # Pass quiz_taker context so template can show name
    return render(request, 'QuizMania/quiz_view.html', {'quiz': quiz, 'questions': questions, 'quiz_taker': quiz_taker})

def results_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    
    # If owner, show ALL. If student, show top 5.
    if request.user == quiz.owner:
        quiz_takers = QuizTaker.objects.filter(quiz=quiz).order_by('-score')
    else:
        quiz_takers = QuizTaker.objects.filter(quiz=quiz).order_by('-score')[:5]
        
    return render(request, 'QuizMania/results.html', {'quiz': quiz, 'quiz_takers': quiz_takers})

def live_count(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    count = QuizTaker.objects.filter(quiz=quiz).count()
    return JsonResponse({'live_count': count})

def live_scoreboard(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz).order_by('-score')
    data = [{'username': taker.alias, 'score': taker.score} for taker in quiz_takers]
    return JsonResponse(data, safe=False)

def live_participants_list(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz)
    data = [{'username': taker.alias} for taker in quiz_takers]
    return JsonResponse(data, safe=False)


@login_required
def live_participants_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    quiz_takers = QuizTaker.objects.filter(quiz=quiz)
    return render(request, 'QuizMania/live_participants.html', {'quiz': quiz, 'quiz_takers': quiz_takers})

# Removed @login_required per user request (Students can see scoreboard)
def live_scoreboard_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    return render(request, 'QuizMania/live_scoreboard.html', {'quiz': quiz})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@login_required
def end_session_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    
    # Only owner can end session
    if request.user != quiz.owner:
        print(f"DEBUG: Unauthorized End Session Attempt. User: {request.user}, Owner: {quiz.owner}", flush=True)
        return redirect('quiz_master_dashboard', quiz_code=quiz_code)

    # Log to file for debugging
    import datetime
    with open("debug_log.txt", "a") as f:
        f.write(f"\n[{datetime.datetime.now()}] END SESSION for {quiz.code}\n")
        f.write(f"Owner: {quiz.owner}, Request User: {request.user}\n")

    # Archive to History
    takers = QuizTaker.objects.filter(quiz=quiz)
    count = takers.count()
    print(f"DEBUG: Found {count} active participants to archive.", flush=True)

    with open("debug_log.txt", "a") as f:
        f.write(f"Found {count} participants to archive.\n")
    
    history_records = []
    for taker in takers:
        print(f"DEBUG: Archiving - Player: {taker.alias}, Score: {taker.score}", flush=True)
        with open("debug_log.txt", "a") as f:
             f.write(f"Archiving: {taker.alias} - Score: {taker.score}\n")
             
        history_records.append(QuizHistory(
            quiz=quiz,
            player_name=taker.alias,
            score=taker.score
        ))
    
    if history_records:
        created = QuizHistory.objects.bulk_create(history_records)
        print(f"DEBUG: Successfully created {len(created)} history records.", flush=True)
        with open("debug_log.txt", "a") as f:
            f.write(f"Successfully created {len(created)} history records.\n")
    else:
        print("DEBUG: No records to archive!", flush=True)
        with open("debug_log.txt", "a") as f:
            f.write("No records to archive!\n")

    # Update quiz timestamp to mark as recently active
    quiz.save()

    # Clear active session (Refresh)
    deleted_count, _ = QuizTaker.objects.filter(quiz=quiz).delete()
    print(f"DEBUG: Deleted {deleted_count} QuizTaker records for quiz {quiz.code}", flush=True)
    
    # Redirect to history page so user sees the result immediately
    return redirect('quiz_history', quiz_code=quiz.code)

def home(request):
    quizzes = []
    quiz_count = 0
    if request.user.is_authenticated:
        # Order by updated_at so most recently used quizzes appear first
        quizzes = Quiz.objects.filter(owner=request.user).order_by('-updated_at')
        quiz_count = quizzes.count()
    return render(request, 'QuizMania/home.html', {'quizzes': quizzes, 'quiz_count': quiz_count})

@login_required
def delete_quiz(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code, owner=request.user)
    if request.method == 'POST':
        quiz.delete()
    return redirect('home')

@login_required
def quiz_history_view(request, quiz_code):
    print(f"DEBUG: History Access - User: {request.user.username}, Quiz: {quiz_code}", flush=True)
    try:
        quiz = Quiz.objects.get(code=quiz_code)
        print(f"DEBUG: Quiz Found. Owner: {quiz.owner.username}", flush=True)
    except Quiz.DoesNotExist:
        print(f"DEBUG: Quiz {quiz_code} Does Not Exist", flush=True)
        return redirect('home')

    if request.user != quiz.owner:
        print(f"DEBUG: ACCESS DENIED. {request.user.username} is not the owner of {quiz_code}", flush=True)
        # For now, allow access to debug? No, stick to logic but maybe show error.
        # return render(request, 'QuizMania/error.html', {'message': 'Only the owner can view history.'})
        # For debugging, we'll let it 404 but now we know why.
    
    quiz = get_object_or_404(Quiz, code=quiz_code, owner=request.user)
    history = QuizHistory.objects.filter(quiz=quiz).order_by('-completed_at')
    print(f"DEBUG: Found {history.count()} history records", flush=True)
    return render(request, 'QuizMania/quiz_history.html', {'quiz': quiz, 'history': history})

@login_required
def delete_quiz_history(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code, owner=request.user)
    if request.method == 'POST':
        QuizHistory.objects.filter(quiz=quiz).delete()
    return redirect('quiz_history', quiz_code=quiz_code)

# Removed @login_required to allow Guests to check their answers
def check_answers_view(request, quiz_code):
    quiz = get_object_or_404(Quiz, code=quiz_code)
    
    quiz_taker = None
    
    # 1. Try Authenticated User
    if request.user.is_authenticated:
        try:
            quiz_taker = QuizTaker.objects.get(quiz=quiz, user=request.user)
        except QuizTaker.DoesNotExist:
            pass
            
    # 2. Try Guest Session
    if not quiz_taker:
        qt_id = request.session.get('quiz_taker_id')
        if qt_id:
            try:
                quiz_taker = QuizTaker.objects.get(id=qt_id, quiz=quiz)
            except QuizTaker.DoesNotExist:
                pass
    
    if not quiz_taker:
        return redirect('home')

    questions = quiz.questions.all()
    user_responses = UserResponse.objects.filter(quiz_taker=quiz_taker)
    response_map = {ur.question.id: ur.selected_choice for ur in user_responses}
    
    review_data = []
    for q in questions:
        selected_choice = response_map.get(q.id)
        is_correct = False
        if selected_choice and selected_choice.is_correct:
            is_correct = True
            
        review_data.append({
            'question': q,
            'selected_choice': selected_choice,
            'choices': q.choices.all(), 
            'is_correct': is_correct
        })
        
    return render(request, 'QuizMania/check_answers.html', {'quiz': quiz, 'review_data': review_data, 'score': quiz_taker.score})

