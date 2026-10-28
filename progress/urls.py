from django.urls import path
from . import views
from .views import StudentDashboardAPIView, StudentCourseLessonProgressAPIView

urlpatterns = [
    # HTML student dashboard
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    # Mark a lesson as complete (HTML)
    path(
        "lesson/<int:lesson_id>/complete/",
        views.mark_lesson_complete,
        name="mark_lesson_complete",
    ),
    # Student dashboard API (JSON)
    path(
        "api/student-dashboard/",
        StudentDashboardAPIView.as_view(),
        name="student_dashboard_api",
    ),
    # Mark a lesson as complete (API)
    path(
        "api/lessons/<int:lesson_id>/complete/",
        views.MarkLessonCompleteAPIView.as_view(),
        name="api_mark_lesson_complete",
    ),
    # Course lesson progress API
    path(
        "api/courses/<slug:slug>/lesson-progress/",
        StudentCourseLessonProgressAPIView.as_view(),
        name="student_course_lesson_progress",
    ),
]
