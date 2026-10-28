from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Count, Q
from certificates.views import is_course_complete
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from courses.models import Lesson, Enrollment, Course
from certificates.models import Certificate
from quizzes.models import QuizAttempt
from .models import LessonProgress
from .serializers import StudentLessonProgressSerializer
from .serializers import DashboardCourseSerializer


@login_required
@require_POST
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    course = lesson.section.course

    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course,
        has_paid=True,
    ).exists()

    if not is_enrolled and not lesson.is_preview:
        raise PermissionDenied("You must enroll in this course to access this lesson.")

    progress, created = LessonProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson,
    )

    if created:
        messages.success(
            request,
            f"Marked '{lesson.title}' as complete.",
        )
    else:
        messages.info(
            request,
            f"'{lesson.title}' is already marked as complete.",
        )

    return redirect("course_detail", slug=course.slug)


@login_required
def student_dashboard(request):
    # Only students can access the student dashboard.
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students can access this dashboard.")

    # Only include courses the student can access.
    enrollments = Enrollment.objects.filter(
        student=request.user,
        has_paid=True,
        course__is_published=True,
    ).select_related("course", "course__instructor")

    dashboard_data = []

    for enrollment in enrollments:
        course = enrollment.course

        # Get all quiz attempts for this student and course.
        quiz_attempts = (
            QuizAttempt.objects.filter(
                student=request.user,
                quiz__lesson__section__course=course,
            )
            .select_related("quiz", "quiz__lesson")
            .order_by("-attempted_at")
        )
        # Count all lessons in this course.
        total_lessons = Lesson.objects.filter(section__course=course).count()

        # Count completed lessons for this student and course.
        completed_lessons = LessonProgress.objects.filter(
            student=request.user,
            lesson__section__course=course,
        ).count()

        # Prevent division by zero.
        percent = (
            int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        )

        certificate = Certificate.objects.filter(
            student=request.user,
            course=course,
        ).first()

        dashboard_data.append(
            {
                "course": course,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "percent": percent,
                "certificate": certificate,
                "quiz_attempts": quiz_attempts,
                "can_generate_certificate": (
                    certificate is None and is_course_complete(request.user, course)
                ),
            }
        )

    return render(
        request,
        "progress/dashboard.html",
        {"dashboard_data": dashboard_data},
    )


class StudentDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.STUDENT:
            return Response(
                {"detail": "Only students can access the student dashboard."},
                status=403,
            )

        enrollments = (
            Enrollment.objects.filter(student=request.user)
            .select_related("course")
            .order_by("-enrolled_at")
        )

        serializer = DashboardCourseSerializer(
            enrollments,
            many=True,
        )

        courses_data = serializer.data

        total_enrolled = len(courses_data)

        completed_courses = sum(
            1 for course in courses_data if course["status"] == "Completed"
        )

        in_progress_courses = total_enrolled - completed_courses

        return Response(
            {
                "student": request.user.username,
                "summary": {
                    "total_enrolled_courses": total_enrolled,
                    "completed_courses": completed_courses,
                    "in_progress_courses": in_progress_courses,
                },
                "enrolled_courses": courses_data,
            }
        )


class MarkLessonCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        # Only students can mark lessons as completed.
        if request.user.role != User.Role.STUDENT:
            return Response(
                {"detail": "Only students can mark lessons as completed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Find the requested lesson.
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        course = lesson.section.course

        # Check whether the student is enrolled in the course.
        is_enrolled = Enrollment.objects.filter(
            student=request.user,
            course=course,
            has_paid=True,
        ).exists()

        # Require enrollment for non-preview lessons.
        if not is_enrolled and not lesson.is_preview:
            return Response(
                {"detail": "You must enroll in this course to complete this lesson."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create a progress record only if one does not already exist.
        progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson,
        )

        # Return a JSON response.
        if created:
            message = "Lesson marked as completed."
        else:
            message = "Lesson is already marked as completed."

        return Response(
            {
                "message": message,
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "completed": True,
            },
            status=status.HTTP_200_OK,
        )


class StudentCourseLessonProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        # Only students can access this API.
        if request.user.role != "STUDENT":
            return Response(
                {"error": "Only students can view lesson progress."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Find the published course using its slug.
        course = Course.objects.filter(
            slug=slug,
            is_published=True,
        ).first()

        if course is None:
            return Response(
                {"error": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check whether the student is enrolled in the course.
        enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course,
            has_paid=True,
        ).first()

        if enrollment is None:
            return Response(
                {"error": "You must be enrolled in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve every lesson belonging to the course.
        lessons = (
            Lesson.objects.filter(
                section__course=course,
            )
            .select_related("section")
            .order_by(
                "section__order",
                "order",
            )
        )

        # Serialize the lessons for this student.
        serializer = StudentLessonProgressSerializer(
            lessons,
            many=True,
            context={"student": request.user},
        )

        # Return the course and lesson progress.
        return Response(
            {
                "course": course.title,
                "slug": course.slug,
                "total_lessons": lessons.count(),
                "completed_lessons": LessonProgress.objects.filter(
                    student=request.user,
                    lesson__section__course=course,
                ).count(),
                "lessons": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
