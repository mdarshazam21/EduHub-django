from django.test import TestCase
from .models import User


class UserModelTest(TestCase):

    def test_create_student(self):
        # Create a student account
        student = User.objects.create_user(
            username="test_student",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        # Check that the student was created
        self.assertEqual(student.username, "test_student")

        # Check that the student's role is correct
        self.assertEqual(student.role, User.Role.STUDENT)

        # Check that the student is active
        self.assertTrue(student.is_active)

        # Check that the password is stored securely
        self.assertTrue(
            student.check_password("TestPassword123!")
        )