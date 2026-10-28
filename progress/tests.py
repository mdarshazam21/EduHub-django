from django.urls import reverse
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import Course, Section, Lesson, Enrollment
from progress.models import LessonProgress
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class StudentDashboardAccessTest(TestCase):

    def setUp(self):
        # Create a student before each test.
        self.student = User.objects.create_user(
            username="dashboard_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

    def test_logged_out_user_cannot_access_dashboard(self):
        # Request the dashboard without logging in.
        response = self.client.get(reverse("student_dashboard"))

        # Unauthenticated users should receive HTTP 403 Forbidden.
        self.assertEqual(response.status_code, 403)

    def test_logged_in_student_can_access_dashboard(self):
        # Log in as a student.
        self.client.login(
            username="dashboard_student",
            password="TestPassword123!",
        )

        # Request the student dashboard.
        response = self.client.get(reverse("student_dashboard"))

        # The student should access the dashboard successfully.
        self.assertEqual(response.status_code, 200)

    def test_instructor_cannot_access_student_dashboard(self):
        # Create an instructor account.
        instructor = User.objects.create_user(
            username="dashboard_instructor",
            password="TestPassword123!",
            role=User.Role.INSTRUCTOR,
        )

        # Log in as the instructor.
        self.client.force_login(instructor)

        # Attempt to access the student dashboard.
        response = self.client.get(reverse("student_dashboard"))

        # The instructor should be denied access.
        self.assertEqual(response.status_code, 403)


class StudentDashboardAPITests(APITestCase):

    def setUp(self):
        # Create an instructor.
        self.instructor = User.objects.create_user(
            username="test_instructor",
            password="TestPassword123!",
            role=User.Role.INSTRUCTOR,
        )

        # Create two students.
        self.student = User.objects.create_user(
            username="test_dashboard_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        self.other_student = User.objects.create_user(
            username="other_dashboard_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        # Create a published course.
        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Dashboard Test Course",
            slug="dashboard-test-course",
            description="A course for dashboard testing.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        # Create a section.
        self.section = Section.objects.create(
            course=self.course,
            title="Introduction",
            order=1,
        )

        # Create three lessons.
        self.lesson1 = Lesson.objects.create(
            section=self.section,
            title="Lesson 1",
            order=1,
        )

        self.lesson2 = Lesson.objects.create(
            section=self.section,
            title="Lesson 2",
            order=2,
        )

        self.lesson3 = Lesson.objects.create(
            section=self.section,
            title="Lesson 3",
            order=3,
        )

        # Enroll the first student in the course.
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

        self.dashboard_url = reverse("student_dashboard")

    def test_dashboard_returns_correct_course_progress(self):
        # Complete one of the three lessons.
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.lesson1,
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["student"], self.student.username)

        summary = response.data["summary"]

        self.assertEqual(summary["total_enrolled_courses"], 1)
        self.assertEqual(summary["completed_courses"], 0)
        self.assertEqual(summary["in_progress_courses"], 1)

        course_data = response.data["enrolled_courses"][0]

        self.assertEqual(course_data["total_lessons"], 3)
        self.assertEqual(course_data["completed_lessons"], 1)
        self.assertEqual(course_data["progress_percentage"], 33)
        self.assertEqual(course_data["status"], "In Progress")

    def test_dashboard_shows_completed_course(self):
        # Complete all three lessons.
        for lesson in [self.lesson1, self.lesson2, self.lesson3]:
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
            )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        summary = response.data["summary"]

        self.assertEqual(summary["completed_courses"], 1)
        self.assertEqual(summary["in_progress_courses"], 0)

        course_data = response.data["enrolled_courses"][0]

        self.assertEqual(course_data["progress_percentage"], 100)
        self.assertEqual(course_data["status"], "Completed")

    def test_student_sees_only_their_own_enrollments(self):
        # The other student is not enrolled in this course.
        self.client.force_authenticate(user=self.other_student)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["total_enrolled_courses"], 0)
        self.assertEqual(response.data["enrolled_courses"], [])

    def test_dashboard_handles_course_without_lessons(self):
        # Create another course with no lessons.
        empty_course = Course.objects.create(
            instructor=self.instructor,
            title="Empty Course",
            slug="empty-course",
            description="A course without lessons.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        Enrollment.objects.create(
            student=self.student,
            course=empty_course,
            has_paid=True,
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        empty_course_data = next(
            item
            for item in response.data["enrolled_courses"]
            if item["course"] == empty_course.id
        )

        self.assertEqual(empty_course_data["total_lessons"], 0)
        self.assertEqual(empty_course_data["completed_lessons"], 0)
        self.assertEqual(empty_course_data["progress_percentage"], 0)
        self.assertEqual(empty_course_data["status"], "In Progress")

    def test_course_with_no_lessons_is_not_completed(self):
        # Create a course with no lessons.
        empty_course = Course.objects.create(
            instructor=self.instructor,
            title="Empty Course",
            slug="empty-course",
            description="A course with no lessons.",
            level="BEGINNER",
            is_free=True,
            price=0,
            is_published=True,
        )

        # Enroll the student in the empty course.
        Enrollment.objects.create(
            student=self.student,
            course=empty_course,
            has_paid=True,
        )

        # Authenticate as the student.
        self.client.force_authenticate(user=self.student)

        # Request the student dashboard.
        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find the empty course in the response.
        empty_course_data = next(
            course
            for course in response.data["enrolled_courses"]
            if course["course"] == empty_course.id
        )

        self.assertEqual(empty_course_data["total_lessons"], 0)
        self.assertEqual(empty_course_data["completed_lessons"], 0)
        self.assertEqual(empty_course_data["remaining_lessons"], 0)
        self.assertEqual(empty_course_data["progress_percentage"], 0)
        self.assertEqual(empty_course_data["status"], "In Progress")


class MarkLessonCompleteAPITests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="lesson_api_instructor",
            password="TestPassword123!",
            role=User.Role.INSTRUCTOR,
        )

        self.student = User.objects.create_user(
            username="lesson_api_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Lesson API Test Course",
            slug="lesson-api-test-course",
            description="A course for testing lesson completion.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        self.section = Section.objects.create(
            course=self.course,
            title="Introduction",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            section=self.section,
            title="Introduction to Python",
            order=1,
        )

        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

        self.url = reverse(
            "api_mark_lesson_complete",
            kwargs={"lesson_id": self.lesson.id},
        )

    def test_student_can_complete_enrolled_lesson(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["completed"])
        self.assertEqual(response.data["lesson_id"], self.lesson.id)

        self.assertTrue(
            LessonProgress.objects.filter(
                student=self.student,
                lesson=self.lesson,
            ).exists()
        )

    def test_repeating_completion_does_not_create_duplicate(self):
        self.client.force_authenticate(user=self.student)

        first_response = self.client.post(self.url)
        second_response = self.client.post(self.url)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            LessonProgress.objects.filter(
                student=self.student,
                lesson=self.lesson,
            ).count(),
            1,
        )

        self.assertIn("already", second_response.data["message"])

    def test_unauthenticated_user_cannot_complete_lesson(self):
        response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_instructor_cannot_complete_lesson(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unenrolled_student_cannot_complete_non_preview_lesson(self):
        other_student = User.objects.create_user(
            username="unenrolled_lesson_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        self.client.force_authenticate(user=other_student)

        response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_nonexistent_lesson_returns_404(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            reverse(
                "api_mark_lesson_complete",
                kwargs={"lesson_id": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class StudentCourseLessonProgressAPITests(APITestCase):
    def setUp(self):
        # Create users with different roles.
        self.student = User.objects.create_user(
            username="progress_student",
            password="testpass123",
            role="STUDENT",
        )

        self.other_student = User.objects.create_user(
            username="other_student",
            password="testpass123",
            role="STUDENT",
        )

        self.instructor = User.objects.create_user(
            username="progress_instructor",
            password="testpass123",
            role="INSTRUCTOR",
        )

        # Create a published course.
        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Python Progress Test",
            slug="python-progress-test",
            description="A course for testing lesson progress.",
            level="BEGINNER",
            is_free=True,
            price=0,
            is_published=True,
        )

        # Create a section and two lessons.
        self.section = Section.objects.create(
            course=self.course,
            title="Python Basics",
            order=0,
        )

        self.completed_lesson = Lesson.objects.create(
            section=self.section,
            title="Introduction to Python",
            content_type="TEXT",
            duration_minutes=5,
            order=0,
            is_preview=True,
        )

        self.incomplete_lesson = Lesson.objects.create(
            section=self.section,
            title="Variables and Data Types",
            content_type="TEXT",
            duration_minutes=10,
            order=1,
            is_preview=False,
        )

        # Enroll the student using the project's enrollment rules.
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

        # Mark only the first lesson as completed.
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.completed_lesson,
        )

        self.url = reverse(
            "student_course_lesson_progress",
            kwargs={"slug": self.course.slug},
        )

    def test_enrolled_student_can_view_lesson_progress(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_lessons"], 2)
        self.assertEqual(response.data["completed_lessons"], 1)
        self.assertEqual(len(response.data["lessons"]), 2)

    def test_completed_and_incomplete_lessons_are_reported_correctly(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        lessons = {lesson["id"]: lesson for lesson in response.data["lessons"]}

        completed = lessons[self.completed_lesson.id]
        incomplete = lessons[self.incomplete_lesson.id]

        self.assertTrue(completed["completed"])
        self.assertIsNotNone(completed["completed_at"])
        self.assertTrue(completed["is_preview"])

        self.assertFalse(incomplete["completed"])
        self.assertIsNone(incomplete["completed_at"])
        self.assertFalse(incomplete["is_preview"])

    def test_instructor_cannot_view_lesson_progress(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unenrolled_student_cannot_view_lesson_progress(self):
        self.client.force_authenticate(user=self.other_student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_course_returns_404(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "student_course_lesson_progress",
            kwargs={"slug": "course-does-not-exist"},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_cannot_view_lesson_progress(self):
        response = self.client.get(self.url)

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
