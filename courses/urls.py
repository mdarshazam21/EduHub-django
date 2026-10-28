from django.urls import path

from . import views
from .views import (
    PublishedCourseListAPIView,
    PublishedCourseDetailAPIView,
    CourseEnrollmentAPIView,
    MyEnrollmentsAPIView,
    CourseReviewListCreateAPIView,
    CourseReviewDetailAPIView,
)

urlpatterns = [
    # ==========================================
    # 1. Course Listing and Student Learning
    # ==========================================
    path(
        "",
        views.course_list,
        name="course_list",
    ),
    path(
        "my-learning/",
        views.my_learning,
        name="my_learning",
    ),
    # ==========================================
    # 2. Instructor Course Management
    # ==========================================
    path(
        "instructor/analytics/",
        views.instructor_analytics,
        name="instructor_analytics",
    ),
    path(
        "instructor/courses/",
        views.instructor_course_list,
        name="instructor_course_list",
    ),
    path(
        "instructor/courses/create/",
        views.instructor_course_create,
        name="instructor_course_create",
    ),
    path(
        "instructor/courses/<slug:slug>/edit/",
        views.instructor_course_edit,
        name="instructor_course_edit",
    ),
    path(
        "instructor/courses/<slug:slug>/delete/",
        views.instructor_course_delete,
        name="instructor_course_delete",
    ),
    # ==========================================
    # 3. Instructor Section Management
    # ==========================================
    path(
        "instructor/courses/<slug:course_slug>/sections/create/",
        views.instructor_section_create,
        name="instructor_section_create",
    ),
    path(
        "instructor/sections/<int:section_id>/edit/",
        views.instructor_section_edit,
        name="instructor_section_edit",
    ),
    path(
        "instructor/sections/<int:section_id>/delete/",
        views.instructor_section_delete,
        name="instructor_section_delete",
    ),
    # ==========================================
    # 4. Instructor Lesson Management
    # ==========================================
    path(
        "instructor/sections/<int:section_id>/lessons/create/",
        views.instructor_lesson_create,
        name="instructor_lesson_create",
    ),
    path(
        "instructor/lessons/<int:lesson_id>/edit/",
        views.instructor_lesson_edit,
        name="instructor_lesson_edit",
    ),
    path(
        "instructor/lessons/<int:lesson_id>/delete/",
        views.instructor_lesson_delete,
        name="instructor_lesson_delete",
    ),
    # ==========================================
    # 5. Course and Review APIs
    # ==========================================
    path(
        "api/courses/",
        PublishedCourseListAPIView.as_view(),
        name="api_course_list",
    ),
    path(
        "api/courses/<slug:slug>/",
        PublishedCourseDetailAPIView.as_view(),
        name="api_course_detail",
    ),
    path(
        "api/courses/<slug:slug>/enroll/",
        CourseEnrollmentAPIView.as_view(),
        name="api_course_enroll",
    ),
    path(
        "api/my-enrollments/",
        MyEnrollmentsAPIView.as_view(),
        name="api_my_enrollments",
    ),
    path(
        "api/courses/<slug:slug>/reviews/",
        CourseReviewListCreateAPIView.as_view(),
        name="api_course_reviews",
    ),
    path(
        "api/courses/<slug:slug>/reviews/<int:pk>/",
        CourseReviewDetailAPIView.as_view(),
        name="api_course_review_detail",
    ),
    # ==========================================
    # 6. Course Enrollment and Reviews
    # ==========================================
    path(
        "<slug:slug>/enroll/",
        views.enroll_in_course,
        name="enroll_in_course",
    ),
    path(
        "<slug:slug>/review/",
        views.submit_review,
        name="submit_review",
    ),
    # ==========================================
    # 7. Student Lesson Viewer and Completion
    # ==========================================
    path(
        "<slug:slug>/lessons/<int:lesson_id>/",
        views.lesson_detail,
        name="lesson_detail",
    ),
    path(
        "lessons/<int:lesson_id>/complete/",
        views.mark_lesson_complete,
        name="mark_lesson_complete",
    ),
    # ==========================================
    # 8. Course Detail — Keep Near the Bottom
    # ==========================================
    path(
        "<slug:slug>/",
        views.course_detail,
        name="course_detail",
    ),
]
