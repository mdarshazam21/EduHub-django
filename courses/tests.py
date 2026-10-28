from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from courses.models import Course, Enrollment, Review
from accounts.models import User


from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

User = get_user_model()


class CourseEnrollmentTest(TestCase):

    def setUp(self):
        # Create a student account.
        self.student = User.objects.create_user(
            username="enrollment_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        # Create an instructor account.
        self.instructor = User.objects.create_user(
            username="enrollment_instructor",
            password="TestPassword123!",
            role=User.Role.INSTRUCTOR,
        )

        # Create a published free course.
        self.course = Course.objects.create(
            title="Test Python Course",
            slug="test-python-course",
            instructor=self.instructor,
            is_published=True,
            price=0,
        )

    def test_student_can_enroll_in_free_course(self):
        # Log in as the student.
        self.client.force_login(self.student)

        # Submit the enrollment form using POST.
        response = self.client.post(
            reverse(
                "enroll_in_course",
                kwargs={"slug": self.course.slug},
            )
        )

        # Enrollment should redirect to the course detail page.
        self.assertRedirects(
            response,
            reverse(
                "course_detail",
                kwargs={"slug": self.course.slug},
            ),
        )

        # Confirm that the enrollment was saved.
        enrollment = Enrollment.objects.get(
            student=self.student,
            course=self.course,
        )

        # A free course should be marked as paid/accessible.
        self.assertTrue(enrollment.has_paid)

    def test_student_cannot_enroll_twice(self):
        # Log in as the student.
        self.client.force_login(self.student)

        enrollment_url = reverse(
            "enroll_in_course",
            kwargs={"slug": self.course.slug},
        )

        # First enrollment request.
        self.client.post(enrollment_url)

        # Second enrollment request.
        self.client.post(enrollment_url)

        # Only one enrollment should exist.
        enrollment_count = Enrollment.objects.filter(
            student=self.student,
            course=self.course,
        ).count()

        self.assertEqual(enrollment_count, 1)

    def test_instructor_cannot_enroll_in_course(self):
        # Log in as the instructor.
        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse(
                "enroll_in_course",
                kwargs={"slug": self.course.slug},
            )
        )

        # The instructor should receive a forbidden response.
        self.assertEqual(response.status_code, 403)

        # No enrollment should be created.
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.instructor,
                course=self.course,
            ).exists()
        )


class PublishedCourseAPITests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="api_instructor",
            email="api_instructor@example.com",
            password="TestPass123!",
            role=User.Role.INSTRUCTOR,
        )

        self.published_course = Course.objects.create(
            instructor=self.instructor,
            title="Python for Beginners",
            slug="python-for-beginners",
            description="Learn Python programming.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        self.unpublished_course = Course.objects.create(
            instructor=self.instructor,
            title="Advanced Django",
            slug="advanced-django",
            description="Learn advanced Django development.",
            level=Course.Level.ADVANCED,
            is_free=False,
            price=500,
            is_published=False,
        )

        self.url = reverse("api_course_list")

    def test_list_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_published_courses_are_returned(self):
        response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "Python for Beginners",
        )

    def test_search_by_title(self):
        response = self.client.get(
            self.url,
            {"search": "Python"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "Python for Beginners",
        )

    def test_filter_by_level(self):
        response = self.client.get(
            self.url,
            {"level": "BEGINNER"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_free_price(self):
        response = self.client.get(
            self.url,
            {"price": "free"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_pagination_response_structure(self):
        response = self.client.get(self.url)

        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)


class CourseEnrollmentAPITests(APITestCase):
    def setUp(self):
        # Create an instructor.
        self.instructor = User.objects.create_user(
            username="enrollment_instructor",
            email="instructor@example.com",
            password="TestPass123!",
            role=User.Role.INSTRUCTOR,
        )

        # Create two students.
        self.student = User.objects.create_user(
            username="enrollment_student",
            email="student@example.com",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.other_student = User.objects.create_user(
            username="other_student",
            email="other@example.com",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        # Create a published free course.
        self.course = Course.objects.create(
            instructor=self.instructor,
            title="API Testing with Python",
            slug="api-testing-python",
            description="Learn API testing.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        # Create an unpublished course.
        self.unpublished_course = Course.objects.create(
            instructor=self.instructor,
            title="Unpublished Course",
            slug="unpublished-course",
            description="This course is not published.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=False,
        )

        # Enrollment API URL.
        self.enroll_url = reverse(
            "api_course_enroll",
            kwargs={"slug": self.course.slug},
        )

        # My enrollments API URL.
        self.my_enrollments_url = reverse("api_my_enrollments")

    def test_unauthenticated_user_cannot_enroll(self):
        response = self.client.post(self.enroll_url, {}, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).exists()
        )

    def test_student_can_enroll_in_free_course(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(self.enroll_url, {}, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).exists()
        )

        enrollment = Enrollment.objects.get(
            student=self.student,
            course=self.course,
        )

        self.assertTrue(enrollment.has_paid)

    def test_duplicate_enrollment_does_not_create_another_record(self):
        self.client.force_authenticate(user=self.student)

        first_response = self.client.post(
            self.enroll_url,
            {},
            format="json",
        )

        second_response = self.client.post(
            self.enroll_url,
            {},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).count(),
            1,
        )

    def test_instructor_cannot_enroll(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.post(self.enroll_url, {}, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_cannot_enroll_in_unpublished_course(self):
        self.client.force_authenticate(user=self.student)

        unpublished_url = reverse(
            "api_course_enroll",
            kwargs={"slug": self.unpublished_course.slug},
        )

        response = self.client.post(
            unpublished_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_student_sees_only_their_own_enrollments(self):
        # Enroll the first student.
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

        # Enroll another student in the same course.
        Enrollment.objects.create(
            student=self.other_student,
            course=self.course,
            has_paid=True,
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.my_enrollments_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 1)

        self.assertEqual(
            response.data["results"][0]["course_title"],
            self.course.title,
        )


class CourseReviewAPITests(APITestCase):
    def setUp(self):
        # Create an instructor.
        self.instructor = User.objects.create_user(
            username="review_instructor",
            email="review_instructor@example.com",
            password="TestPass123!",
            role=User.Role.INSTRUCTOR,
        )

        # Create two students.
        self.student = User.objects.create_user(
            username="review_student",
            email="review_student@example.com",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.other_student = User.objects.create_user(
            username="review_other_student",
            email="review_other_student@example.com",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        # Create a published course.
        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Review Testing Course",
            slug="review-testing-course",
            description="A course for testing reviews.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        # Create a second published course.
        self.other_course = Course.objects.create(
            instructor=self.instructor,
            title="Another Review Course",
            slug="another-review-course",
            description="Another course for review testing.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        self.review_url = reverse(
            "api_course_reviews",
            kwargs={"slug": self.course.slug},
        )

        # Enroll the first student in the first course.
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

    def test_anyone_can_list_reviews(self):
        response = self.client.get(self.review_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_enrolled_student_can_create_review(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Excellent course!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["student_username"], self.student.username)
        self.assertEqual(response.data["rating"], 5)

    def test_unauthenticated_user_cannot_create_review(self):
        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Excellent course!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_review_without_enrollment(self):
        self.client.force_authenticate(user=self.other_student)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Testing enrollment restriction."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "You must be enrolled in this course to submit a review.",
        )

    def test_student_cannot_review_paid_course_before_payment(self):
        # Create a paid course.
        course = Course.objects.create(
            title="Paid Course",
            instructor=self.instructor,
            is_free=False,
            price=1000,
            is_published=True,
        )

        # Create an enrollment that has not been paid.
        Enrollment.objects.create(
            student=self.student,
            course=course,
            has_paid=False,
        )

        # Log in as the student.
        self.client.force_authenticate(user=self.student)

        # Try to submit a review.
        unpaid_review_url = reverse(
            "api_course_reviews",
            kwargs={"slug": course.slug},
        )

        response = self.client.post(
            unpaid_review_url,
            {
                "rating": 5,
                "comment": "Excellent course!",
            },
            format="json",
        )

        # The API should reject the review.
        self.assertEqual(response.status_code, 403)

        # No review should have been created.
        self.assertFalse(
            Review.objects.filter(
                student=self.student,
                course=course,
            ).exists()
        )

    def test_student_cannot_submit_duplicate_review(self):
        self.client.force_authenticate(user=self.student)

        payload = {"rating": 4, "comment": "Very good course."}

        first_response = self.client.post(
            self.review_url,
            payload,
            format="json",
        )

        second_response = self.client.post(
            self.review_url,
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            second_response.data["detail"],
            "You have already reviewed this course.",
        )

    def test_instructor_cannot_create_review(self):
        self.client.force_authenticate(user=self.instructor)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Testing instructor permissions."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "Only students can submit reviews.",
        )

    def test_rating_below_one_is_rejected(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 0, "comment": "Invalid rating."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_above_five_is_rejected(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 6, "comment": "Invalid rating."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_can_review_another_course(self):
        # Enroll the student in the second course.
        Enrollment.objects.create(
            student=self.student,
            course=self.other_course,
            has_paid=True,
        )

        self.client.force_authenticate(user=self.student)

        other_review_url = reverse(
            "api_course_reviews",
            kwargs={"slug": self.other_course.slug},
        )

        response = self.client.post(
            other_review_url,
            {"rating": 4, "comment": "Reviewing another course."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_can_update_own_review(self):
        self.client.force_authenticate(user=self.student)

        create_response = self.client.post(
            self.review_url,
            {"rating": 4, "comment": "Good course."},
            format="json",
        )
        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )

        review_id = create_response.data["id"]
        detail_url = reverse(
            "api_course_review_detail",
            kwargs={"slug": self.course.slug, "pk": review_id},
        )

        response = self.client.patch(
            detail_url,
            {"rating": 5, "comment": "Excellent course!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating"], 5)
        self.assertEqual(response.data["comment"], "Excellent course!")

    def test_student_cannot_update_another_students_review(self):
        from courses.models import Review

        review = Review.objects.create(
            student=self.student,
            course=self.course,
            rating=4,
            comment="My review.",
        )

        self.client.force_authenticate(user=self.other_student)

        detail_url = reverse(
            "api_course_review_detail",
            kwargs={"slug": self.course.slug, "pk": review.pk},
        )

        response = self.client.patch(
            detail_url,
            {"rating": 1, "comment": "Trying to change another review."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_delete_own_review(self):
        from courses.models import Review

        review = Review.objects.create(
            student=self.student,
            course=self.course,
            rating=4,
            comment="Review to delete.",
        )

        self.client.force_authenticate(user=self.student)

        detail_url = reverse(
            "api_course_review_detail",
            kwargs={"slug": self.course.slug, "pk": review.pk},
        )

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_student_cannot_delete_another_students_review(self):
        from courses.models import Review

        review = Review.objects.create(
            student=self.student,
            course=self.course,
            rating=4,
            comment="My review.",
        )

        self.client.force_authenticate(user=self.other_student)

        detail_url = reverse(
            "api_course_review_detail",
            kwargs={"slug": self.course.slug, "pk": review.pk},
        )

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())


class CourseRatingSummaryTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="rating_instructor",
            email="rating_instructor@example.com",
            password="TestPass123!",
            role=User.Role.INSTRUCTOR,
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Rating Test Course",
            slug="rating-test-course",
            description="A course for testing ratings.",
            level=Course.Level.BEGINNER,
            is_free=True,
            price=0,
            is_published=True,
        )

        self.url = reverse(
            "api_course_list",
        )

    def test_course_rating_summary_is_correct(self):
        from courses.models import Review

        student1 = User.objects.create_user(
            username="rating_student1",
            email="rating_student1@example.com",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        student2 = User.objects.create_user(
            username="rating_student2",
            email="rating_student2@example.com",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        Review.objects.create(
            student=student1,
            course=self.course,
            rating=4,
            comment="Good course.",
        )

        Review.objects.create(
            student=student2,
            course=self.course,
            rating=5,
            comment="Excellent course.",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        course_data = next(
            item
            for item in response.data["results"]
            if item["slug"] == self.course.slug
        )

        self.assertEqual(course_data["average_rating"], 4.5)
        self.assertEqual(course_data["total_reviews"], 2)
        self.assertEqual(
            course_data["rating_distribution"],
            {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1},
        )

    def test_course_without_reviews_has_zero_values(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        course_data = next(
            item
            for item in response.data["results"]
            if item["slug"] == self.course.slug
        )

        self.assertEqual(course_data["average_rating"], 0)
        self.assertEqual(course_data["total_reviews"], 0)
        self.assertEqual(
            course_data["rating_distribution"],
            {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        )
