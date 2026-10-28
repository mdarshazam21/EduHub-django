from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Course, Enrollment, Review
from accounts.models import User
from .forms import ReviewForm, CourseForm
from django.db.models import Avg
from django.views.decorators.http import require_POST
from .forms import SectionForm, LessonForm
from .models import Section, Lesson
from courses.models import Course, Enrollment, Lesson
from progress.models import LessonProgress

from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Course
from .serializers import CourseSerializer, EnrollmentSerializer, ReviewSerializer

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied as APIPermissionDenied
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.filters import OrderingFilter


def course_list(request):
    # Step 1: Get all published courses.
    if request.user.is_authenticated and request.user.role == "INSTRUCTOR":
        courses = Course.objects.filter(
            Q(is_published=True) | Q(instructor=request.user)
        )
    else:
        courses = Course.objects.filter(is_published=True)

    # Step 2: Get the search query.
    query = request.GET.get("q", "").strip()

    if query:
        courses = courses.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    # Step 3: Filter courses by level.
    level = request.GET.get("level", "")

    valid_levels = {value for value, label in Course.Level.choices}

    if level in valid_levels:
        courses = courses.filter(level=level)

    # Step 4: Filter courses by price.
    price_filter = request.GET.get("price", "")

    if price_filter == "free":
        courses = courses.filter(is_free=True)

    elif price_filter == "paid":
        courses = courses.filter(is_free=False)

    # Step 5: Paginate the results.
    paginator = Paginator(courses, 9)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Step 6: Send the data to the template.
    context = {
        "page_obj": page_obj,
        "query": query,
        "level": level,
        "price_filter": price_filter,
        "levels": Course.Level.choices,
    }

    return render(
        request,
        "courses/course_list.html",
        context,
    )


def course_detail(request, slug):
    # Find the course, whether published or unpublished.
    course = get_object_or_404(Course, slug=slug)

    # Determine whether the current user owns this course.
    is_owner = request.user.is_authenticated and course.instructor_id == request.user.pk

    # Students and other visitors must not access unpublished courses.
    if not course.is_published and not is_owner:
        from django.http import Http404

        raise Http404("This course is not available.")

    # Find the current user's enrollment, if one exists.
    enrollment = None

    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).first()

    is_enrolled = enrollment is not None

    # A paid course requires a paid enrollment to unlock its lessons.
    has_access = course.is_free or (enrollment is not None and enrollment.has_paid)

    context = {
        "course": course,
        "enrollment": enrollment,
        "is_enrolled": is_enrolled,
        "has_access": has_access,
        "is_owner": is_owner,
    }

    return render(
        request,
        "courses/course_detail.html",
        context,
    )


@login_required
@require_POST
def enroll_in_course(request, slug):
    course = get_object_or_404(
        Course,
        slug=slug,
        is_published=True,
    )

    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students can enroll in courses.")

    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={
            "has_paid": course.is_free,
        },
    )

    if not created:
        messages.info(
            request,
            "You are already enrolled in this course.",
        )
    elif course.is_free:
        messages.success(
            request,
            "You have successfully enrolled in this free course!",
        )
    else:
        messages.info(
            request,
            "Enrollment created. Please complete payment to access this course.",
        )

    return redirect("course_detail", slug=course.slug)


@login_required
def submit_review(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)

    is_enrolled = Enrollment.objects.filter(
        student=request.user, course=course, has_paid=True
    ).exists()
    if not is_enrolled:
        raise PermissionDenied("You must be enrolled in this course to leave a review.")

    if Review.objects.filter(course=course, student=request.user).exists():
        messages.info(request, "You have already reviewed this course.")
        return redirect("course_detail", slug=course.slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.student = request.user
            review.save()
            messages.success(request, "Thank you for your review!")
            return redirect("course_detail", slug=course.slug)
    else:
        form = ReviewForm()

    return render(request, "courses/review_form.html", {"form": form, "course": course})


@login_required
def instructor_analytics(request):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can view analytics.")

    courses = Course.objects.filter(instructor=request.user)

    analytics_data = []
    for course in courses:
        total_enrollments = course.enrollments.filter(has_paid=True).count()
        total_revenue = total_enrollments * course.price if not course.is_free else 0
        avg_rating = course.reviews.aggregate(Avg("rating"))["rating__avg"]

        analytics_data.append(
            {
                "course": course,
                "total_enrollments": total_enrollments,
                "total_revenue": total_revenue,
                "avg_rating": avg_rating,
            }
        )

    return render(
        request, "courses/instructor_analytics.html", {"analytics_data": analytics_data}
    )


@login_required
def instructor_course_list(request):
    # Only instructors can access this page.
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage courses.")

    # Retrieve only courses created by the logged-in instructor.
    courses = Course.objects.filter(instructor=request.user).order_by("-created_at")

    return render(
        request,
        "courses/instructor_course_list.html",
        {"courses": courses},
    )


@login_required
def instructor_course_create(request):
    # Only instructors can create courses.
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can create courses.")

    if request.method == "POST":
        # Populate the form with submitted data and uploaded files.
        form = CourseForm(request.POST, request.FILES)

        if form.is_valid():
            # Create the course object without saving it yet.
            course = form.save(commit=False)

            # Assign the logged-in instructor as the course owner.
            course.instructor = request.user

            # Save the course to the database.
            course.save()

            messages.success(request, "Course created successfully!")

            return redirect("instructor_course_list")

    else:
        # Display an empty form for a new course.
        form = CourseForm()

    return render(
        request,
        "courses/instructor_course_form.html",
        {
            "form": form,
            "page_title": "Create Course",
        },
    )


@login_required
def instructor_course_edit(request, slug):
    # Only instructors can edit courses.
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can edit courses.")

    # Find the course only if it belongs to the logged-in instructor.
    course = get_object_or_404(
        Course,
        slug=slug,
        instructor=request.user,
    )

    if request.method == "POST":
        # Load submitted data and any newly uploaded thumbnail.
        form = CourseForm(request.POST, request.FILES, instance=course)

        if form.is_valid():
            form.save()

            messages.success(request, "Course updated successfully!")

            return redirect("instructor_course_list")

    else:
        # Pre-fill the form with the existing course information.
        form = CourseForm(instance=course)

    return render(
        request,
        "courses/instructor_course_form.html",
        {
            "form": form,
            "course": course,
            "page_title": "Edit Course",
        },
    )


@login_required
@require_POST
def instructor_course_delete(request, slug):
    # Step 1: Only instructors can delete courses.
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can delete courses.")

    # Step 2: Find the course owned by the logged-in instructor.
    course = get_object_or_404(
        Course,
        slug=slug,
        instructor=request.user,
    )

    # Step 3: Store the title for the success message.
    course_title = course.title

    # Step 4: Delete the course from the database.
    course.delete()

    # Step 5: Notify the instructor.
    messages.success(
        request,
        f'Course "{course_title}" deleted successfully!',
    )

    # Step 6: Return to the instructor's course list.
    return redirect("instructor_course_list")


class PublishedCourseListAPIView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    filter_backends = [OrderingFilter]
    ordering_fields = ["price", "created_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        courses = Course.objects.filter(is_published=True)

        # Search by course title or description.
        search_query = self.request.query_params.get("search", "").strip()

        if search_query:
            courses = courses.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        # Filter by course level.
        level = self.request.query_params.get("level", "").strip().upper()

        valid_levels = {value for value, label in Course.Level.choices}

        if level in valid_levels:
            courses = courses.filter(level=level)

        # Filter by price category.
        price_filter = self.request.query_params.get("price", "").strip().lower()

        if price_filter == "free":
            courses = courses.filter(is_free=True)
        elif price_filter == "paid":
            courses = courses.filter(is_free=False)

        return courses


class PublishedCourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return Course.objects.filter(is_published=True)


class CourseEnrollmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        # Find the published course.
        course = get_object_or_404(
            Course,
            slug=slug,
            is_published=True,
        )

        # Only students can enroll.
        if request.user.role != User.Role.STUDENT:
            raise APIPermissionDenied("Only students can enroll in courses.")

        # Create an enrollment if one doesn't already exist.
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={
                "has_paid": course.is_free,
            },
        )

        serializer = EnrollmentSerializer(enrollment)

        if created:
            return Response(
                {
                    "message": "Enrollment successful.",
                    "enrollment": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "message": "You are already enrolled in this course.",
                "enrollment": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class MyEnrollmentsAPIView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).select_related(
            "course"
        )


class CourseReviewListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(
            course__slug=self.kwargs["slug"],
            course__is_published=True,
        ).select_related("student", "course")

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        course = get_object_or_404(
            Course,
            slug=self.kwargs["slug"],
            is_published=True,
        )

        if self.request.user.role != User.Role.STUDENT:
            raise APIPermissionDenied("Only students can submit reviews.")

        is_enrolled = Enrollment.objects.filter(
            student=self.request.user, course=course, has_paid=True
        ).exists()

        if not is_enrolled:
            raise APIPermissionDenied(
                "You must be enrolled in this course to submit a review."
            )

        if Review.objects.filter(
            student=self.request.user,
            course=course,
        ).exists():
            raise APIPermissionDenied("You have already reviewed this course.")

        serializer.save(
            student=self.request.user,
            course=course,
        )


class CourseReviewDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(
            course__slug=self.kwargs["slug"],
            course__is_published=True,
        ).select_related("student", "course")

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        review = self.get_object()

        if self.request.user.role != User.Role.STUDENT:
            raise APIPermissionDenied("Only students can update reviews.")

        if review.student != self.request.user:
            raise APIPermissionDenied("You can only update your own review.")

        serializer.save(
            student=review.student,
            course=review.course,
        )

    def perform_destroy(self, instance):
        if self.request.user.role != User.Role.STUDENT:
            raise APIPermissionDenied("Only students can delete reviews.")

        if instance.student != self.request.user:
            raise APIPermissionDenied("You can only delete your own review.")

        instance.delete()


# Create a new section inside an instructor's course
@login_required
def instructor_section_create(request, course_slug):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage sections.")

    course = get_object_or_404(
        Course,
        slug=course_slug,
        instructor=request.user,
    )

    if request.method == "POST":
        form = SectionForm(request.POST)

        if form.is_valid():
            section = form.save(commit=False)
            section.course = course
            section.save()

            messages.success(request, "Section created successfully!")
            return redirect("instructor_course_list")

    else:
        form = SectionForm()

    return render(
        request,
        "courses/section_form.html",
        {
            "form": form,
            "course": course,
            "page_title": "Create Section",
        },
    )


# Edit an existing section
@login_required
def instructor_section_edit(request, section_id):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage sections.")

    section = get_object_or_404(
        Section,
        id=section_id,
        course__instructor=request.user,
    )

    if request.method == "POST":
        form = SectionForm(request.POST, instance=section)

        if form.is_valid():
            form.save()
            messages.success(request, "Section updated successfully!")
            return redirect("instructor_course_list")

    else:
        form = SectionForm(instance=section)

    return render(
        request,
        "courses/section_form.html",
        {
            "form": form,
            "course": section.course,
            "section": section,
            "page_title": "Edit Section",
        },
    )


# Delete a section
@login_required
@require_POST
def instructor_section_delete(request, section_id):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage sections.")

    section = get_object_or_404(
        Section,
        id=section_id,
        course__instructor=request.user,
    )

    section.delete()

    messages.success(request, "Section deleted successfully!")
    return redirect("instructor_course_list")


# Create a lesson inside one of the instructor's sections
@login_required
def instructor_lesson_create(request, section_id):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage lessons.")

    section = get_object_or_404(
        Section,
        id=section_id,
        course__instructor=request.user,
    )

    if request.method == "POST":
        form = LessonForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.section = section
            lesson.save()

            messages.success(request, "Lesson created successfully!")
            return redirect("instructor_course_list")

    else:
        form = LessonForm()

    return render(
        request,
        "courses/lesson_form.html",
        {
            "form": form,
            "section": section,
            "course": section.course,
            "page_title": "Create Lesson",
        },
    )


# Edit an existing lesson
@login_required
def instructor_lesson_edit(request, lesson_id):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage lessons.")

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        section__course__instructor=request.user,
    )

    if request.method == "POST":
        form = LessonForm(
            request.POST,
            request.FILES,
            instance=lesson,
        )

        if form.is_valid():
            form.save()

            messages.success(request, "Lesson updated successfully!")
            return redirect("instructor_course_list")

    else:
        form = LessonForm(instance=lesson)

    return render(
        request,
        "courses/lesson_form.html",
        {
            "form": form,
            "lesson": lesson,
            "section": lesson.section,
            "course": lesson.section.course,
            "page_title": "Edit Lesson",
        },
    )


# Delete an existing lesson
@login_required
@require_POST
def instructor_lesson_delete(request, lesson_id):
    if request.user.role != User.Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can manage lessons.")

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        section__course__instructor=request.user,
    )

    lesson.delete()

    messages.success(request, "Lesson deleted successfully!")
    return redirect("instructor_course_list")


# Display courses that the logged-in student has enrolled in
@login_required
def my_learning(request):
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students can access My Learning.")

    enrollments = (
        Enrollment.objects.filter(student=request.user)
        .select_related("course")
        .annotate(
            total_lessons=Count(
                "course__sections__lessons",
                distinct=True,
            ),
            completed_lessons=Count(
                "course__sections__lessons__progress_records",
                filter=Q(
                    course__sections__lessons__progress_records__student=request.user
                ),
                distinct=True,
            ),
        )
        .order_by("-enrolled_at")
    )

    for enrollment in enrollments:
        if enrollment.total_lessons:
            enrollment.progress_percentage = round(
                enrollment.completed_lessons / enrollment.total_lessons * 100
            )
        else:
            enrollment.progress_percentage = 0

    return render(
        request,
        "courses/my_learning.html",
        {"enrollments": enrollments},
    )


@login_required
def lesson_detail(request, slug, lesson_id):

    # Find the published course.
    course = get_object_or_404(
        Course,
        slug=slug,
        is_published=True,
    )

    # Find the lesson and ensure it belongs to this course.
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        section__course=course,
    )

    # Only students can access the student lesson viewer.
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students can access lessons.")

    # Find the student's enrollment, if one exists.
    enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
    ).first()

    # Preview lessons are available without enrollment.
    if not lesson.is_preview:
        if enrollment is None:
            raise PermissionDenied(
                "You must enroll in this course to view this lesson."
            )

        # Paid courses require confirmed payment.
        if not course.is_free and not enrollment.has_paid:
            raise PermissionDenied("Payment is required to view this lesson.")

    # Check whether the current lesson is completed.
    is_completed = LessonProgress.objects.filter(
        student=request.user,
        lesson=lesson,
    ).exists()

    # Retrieve all lessons in the course in curriculum order.
    lessons = list(
        Lesson.objects.filter(
            section__course=course,
        )
        .select_related("section")
        .order_by(
            "section__order",
            "order",
            "id",
        )
    )

    # Find the current lesson's position.
    current_index = next(
        index
        for index, course_lesson in enumerate(lessons)
        if course_lesson.id == lesson.id
    )

    # Find the previous and next lessons, if available.
    previous_lesson = lessons[current_index - 1] if current_index > 0 else None

    next_lesson = (
        lessons[current_index + 1] if current_index < len(lessons) - 1 else None
    )

    # Retrieve all sections in their configured order.
    curriculum_sections = course.sections.prefetch_related("lessons").all()

    # Get IDs of lessons completed by the current student.
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            student=request.user,
            lesson__section__course=course,
        ).values_list(
            "lesson_id",
            flat=True,
        )
    )

    return render(
        request,
        "courses/lesson_detail.html",
        {
            "course": course,
            "lesson": lesson,
            "lessons": lessons,
            "section": lesson.section,
            "is_completed": is_completed,
            "enrollment": enrollment,
            "previous_lesson": previous_lesson,
            "next_lesson": next_lesson,
            "curriculum_sections": curriculum_sections,
            "completed_lesson_ids": completed_lesson_ids,
        },
    )


@login_required
@require_POST
def mark_lesson_complete(request, lesson_id):
    """Record lesson completion for the current student."""

    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students can mark lessons as complete.")

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id,
        section__course__is_published=True,
    )

    course = lesson.section.course

    enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
    ).first()

    # Completion requires enrollment, including preview lessons.
    if enrollment is None:
        raise PermissionDenied("Enroll in the course before completing lessons.")

    if not course.is_free and not enrollment.has_paid:
        raise PermissionDenied("Payment is required to complete this lesson.")

    LessonProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson,
    )

    return redirect(
        "lesson_detail",
        slug=course.slug,
        lesson_id=lesson.id,
    )
