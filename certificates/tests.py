from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from courses.models import Course, Enrollment, Section, Lesson
from progress.models import LessonProgress
from certificates.models import Certificate

User = get_user_model()


class CertificateGenerationTest(TestCase):

    def setUp(self):
        # Create a student account.
        self.student = User.objects.create_user(
            username="certificate_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        # Create an instructor account.
        self.instructor = User.objects.create_user(
            username="certificate_instructor",
            password="TestPassword123!",
            role=User.Role.INSTRUCTOR,
        )

        # Create a published free course.
        self.course = Course.objects.create(
            title="Certificate Test Course",
            slug="certificate-test-course",
            instructor=self.instructor,
            is_published=True,
            price=0,
        )

        # Enroll the student with confirmed access.
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

    def test_student_cannot_get_certificate_before_completion(self):
        # Log in as the student.
        self.client.force_login(self.student)

        # Request a certificate before completing the course.
        response = self.client.get(
            reverse(
                "generate_certificate",
                kwargs={"slug": self.course.slug},
            )
        )

        # The student should be redirected to the course page.
        self.assertRedirects(
            response,
            reverse(
                "course_detail",
                kwargs={"slug": self.course.slug},
            ),
        )

        # No certificate should be created.
        self.assertFalse(
            Certificate.objects.filter(
                student=self.student,
                course=self.course,
            ).exists()
        )

    def test_student_can_generate_certificate_after_completion(self):
        # Create a section in the course.
        section = Section.objects.create(
            course=self.course,
            title="Python Fundamentals",
            order=1,
        )

        # Create a lesson in that section.
        lesson = Lesson.objects.create(
            section=section,
            title="Introduction to Python",
            content_type=Lesson.ContentType.TEXT,
            text_content="Introduction to Python programming.",
            duration_minutes=10,
            order=1,
        )

        # Mark the lesson as completed.
        LessonProgress.objects.create(
            student=self.student,
            lesson=lesson,
        )

        # Log in as the student.
        self.client.force_login(self.student)

        # Request certificate generation.
        response = self.client.get(
            reverse(
                "generate_certificate",
                kwargs={"slug": self.course.slug},
            )
        )

        # Confirm that the certificate was created.
        certificate = Certificate.objects.get(
            student=self.student,
            course=self.course,
        )

        # Confirm redirection to the certificate page.
        self.assertRedirects(
            response,
            reverse(
                "view_certificate",
                kwargs={
                    "certificate_id": certificate.certificate_id,
                },
            ),
        )

        # Confirm that only one certificate exists.
        self.assertEqual(
            Certificate.objects.filter(
                student=self.student,
                course=self.course,
            ).count(),
            1,
        )


    def test_student_cannot_receive_duplicate_certificates(self):
        # Create a section.
        section = Section.objects.create(
            course=self.course,
            title="Python Fundamentals",
            order=1,
        )

        # Create a lesson.
        lesson = Lesson.objects.create(
            section=section,
            title="Introduction to Python",
            content_type=Lesson.ContentType.TEXT,
            text_content="Introduction to Python programming.",
            duration_minutes=10,
            order=1,
        )

        # Mark the lesson as completed.
        LessonProgress.objects.create(
            student=self.student,
            lesson=lesson,
        )

        # Log in as the student.
        self.client.force_login(self.student)

        # Request the certificate for the first time.
        self.client.get(
            reverse(
                "generate_certificate",
                kwargs={"slug": self.course.slug},
            )
        )

        # Save the first certificate's ID.
        first_certificate = Certificate.objects.get(
            student=self.student,
            course=self.course,
        )

        # Request the certificate again.
        response = self.client.get(
            reverse(
                "generate_certificate",
                kwargs={"slug": self.course.slug},
            )
        )

        # Retrieve the certificate again.
        second_certificate = Certificate.objects.get(
            student=self.student,
            course=self.course,
        )

        # Both requests should refer to the same certificate.
        self.assertEqual(
            first_certificate.certificate_id,
            second_certificate.certificate_id,
        )

        # Only one certificate should exist for this student and course.
        self.assertEqual(
            Certificate.objects.filter(
                student=self.student,
                course=self.course,
            ).count(),
            1,
        )

        # The second request should redirect to the existing certificate.
        self.assertRedirects(
            response,
            reverse(
                "view_certificate",
                kwargs={
                    "certificate_id": first_certificate.certificate_id,
                },
            ),
        )
