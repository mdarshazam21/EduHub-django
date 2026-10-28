from django.urls import path
from . import views

urlpatterns = [
    path("<int:quiz_id>/take/", views.take_quiz, name="take_quiz"),
    path("result/<int:attempt_id>/", views.quiz_result, name="quiz_result"),
    path(
        "api/<int:quiz_id>/",
        views.QuizDetailAPIView.as_view(),
        name="api_quiz_detail",
    ),
    path(
        "api/<int:quiz_id>/submit/",
        views.QuizSubmitAPIView.as_view(),
        name="api_quiz_submit",
    ),
    path(
        "api/attempts/<int:attempt_id>/",
        views.QuizAttemptDetailAPIView.as_view(),
        name="api_quiz_attempt_detail",
    ),
    path(
        "api/my-attempts/",
        views.QuizAttemptHistoryAPIView.as_view(),
        name="quiz-attempt-history",
    ),
]
