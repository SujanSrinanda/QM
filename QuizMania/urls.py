
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ai_quiz_generator/', views.ai_quiz_generator, name='ai_quiz_generator'),
    path('review_generated_quiz/', views.review_generated_quiz, name='review_generated_quiz'),
    path('start_session/', views.start_session, name='start_session'),
    path('quiz/<str:quiz_code>/', views.quiz_master_dashboard, name='quiz_master_dashboard'),
    path('join_session/', views.join_session, name='join_session'),
    path('quiz/<str:quiz_code>/results/', views.results_view, name='results_view'),
    path('api/quiz/<str:quiz_code>/live_count/', views.live_count, name='live_count'),
    path('api/quiz/<str:quiz_code>/live_scoreboard/', views.live_scoreboard, name='live_scoreboard'),
    path('api/quiz/<str:quiz_code>/live_participants_list/', views.live_participants_list, name='live_participants_list'),
    path('quiz/<str:quiz_code>/live_participants/', views.live_participants_view, name='live_participants'),
    path('quiz/<str:quiz_code>/live_scoreboard/', views.live_scoreboard_view, name='live_scoreboard_view'),
    path('quiz/<str:quiz_code>/end/', views.end_session_view, name='end_session'),
    path('quiz/<str:quiz_code>/history/', views.quiz_history_view, name='quiz_history'),
    path('quiz/<str:quiz_code>/history/delete/', views.delete_quiz_history, name='delete_quiz_history'),
    path('quiz/<str:quiz_code>/delete/', views.delete_quiz, name='delete_quiz'),
    path('quiz/<str:quiz_code>/check_answers/', views.check_answers_view, name='check_answers'),
    path('quiz/<str:quiz_code>/<str:username>/', views.quiz_view, name='quiz_view'),
]
