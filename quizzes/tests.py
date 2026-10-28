from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import User
from courses.models import Course, Section, Lesson, Enrollment
from .models import Quiz, Question, Choice, QuizAttempt, QuizAnswer


class QuizAttemptHistoryAPITests(APITestCase):

    def setUp(self):
        # Create two students
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="testpass123",
            role="STUDENT",
        )

        self.other_student = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="testpass123",
            role="STUDENT",
        )

        # Create an instructor
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password="testpass123",
            role="INSTRUCTOR",
        )

        # Create a course
        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Python Testing Course",
            slug="python-testing-course",
            description="A course created for automated tests.",
            level="BEGINNER",
            is_free=True,
            price=0,
            is_published=True,
        )

        # Create a section
        self.section = Section.objects.create(
            course=self.course,
            title="Python Basics",
            order=1,
        )

        # Create a lesson
        self.lesson = Lesson.objects.create(
            section=self.section,
            title="Python Variables",
            content_type="TEXT",
            text_content="Variables store values.",
            duration_minutes=10,
            order=1,
        )

        # Create a quiz
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title="Python Variables Quiz",
            passing_score=70,
        )

        # Create a question and its choices
        self.question = Question.objects.create(
            quiz=self.quiz,
            text="Which keyword defines a function in Python?",
            order=1,
        )

        self.correct_choice = Choice.objects.create(
            question=self.question,
            text="def",
            is_correct=True,
        )

        self.incorrect_choice = Choice.objects.create(
            question=self.question,
            text="classify",
            is_correct=False,
        )

        # Enroll both students with access to the course
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

        Enrollment.objects.create(
            student=self.other_student,
            course=self.course,
            has_paid=True,
        )

        # Create a quiz attempt for each student
        self.student_attempt = QuizAttempt.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=100,
            passed=True,
        )

        self.other_student_attempt = QuizAttempt.objects.create(
            student=self.other_student,
            quiz=self.quiz,
            score=0,
            passed=False,
        )

    def test_student_sees_only_own_attempts(self):
        self.client.force_authenticate(user=self.student)

        url = "/quizzes/api/my-attempts/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        attempts = response.data["results"]

        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["id"], self.student_attempt.id)
        self.assertEqual(
            attempts[0]["quiz_title"],
            "Python Variables Quiz",
        )

    def test_unauthenticated_user_cannot_access_history(self):
        url = "/quizzes/api/my-attempts/"
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_instructor_cannot_access_student_history(self):
        self.client.force_authenticate(user=self.instructor)

        url = "/quizzes/api/my-attempts/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_attempts_are_ordered_newest_first(self):
        self.client.force_authenticate(user=self.student)

        older_attempt = self.student_attempt

        newer_attempt = QuizAttempt.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=80,
            passed=True,
        )

        url = "/quizzes/api/my-attempts/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

        attempts = response.data["results"]

        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["id"], newer_attempt.id)
        self.assertEqual(attempts[1]["id"], older_attempt.id)

    def test_attempt_history_can_be_filtered_by_quiz_id(self):
        self.client.force_authenticate(user=self.student)

        url = f"/quizzes/api/my-attempts/?quiz_id={self.quiz.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        attempts = response.data["results"]

        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["id"], self.student_attempt.id)

    def test_attempt_history_returns_empty_for_quiz_without_attempts(self):
        self.client.force_authenticate(user=self.student)

        another_lesson = Lesson.objects.create(
            section=self.section,
            title="Python Functions",
            content_type="TEXT",
            text_content="Functions are reusable blocks of code.",
            duration_minutes=15,
            order=2,
        )

        another_quiz = Quiz.objects.create(
            lesson=another_lesson,
            title="Python Functions Quiz",
            passing_score=70,
        )

        url = f"/quizzes/api/my-attempts/?quiz_id={another_quiz.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_attempt_history_rejects_non_numeric_quiz_id(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("quiz-attempt-history") + "?quiz_id=abc"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attempt_history_rejects_zero_quiz_id(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("quiz-attempt-history") + "?quiz_id=0"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attempt_history_rejects_negative_quiz_id(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("quiz-attempt-history") + "?quiz_id=-1"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attempt_history_returns_paginated_response(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("quiz-attempt-history")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertIsInstance(response.data["results"], list)

    def test_attempt_history_respects_page_size(self):
        self.client.force_authenticate(user=self.student)

        # Create six additional attempts.
        for index in range(6):
            QuizAttempt.objects.create(
                student=self.student,
                quiz=self.quiz,
                score=80,
                passed=True,
            )

        url = reverse("quiz-attempt-history")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # One existing attempt + six new attempts = seven.
        self.assertEqual(response.data["count"], 7)

        # Only five attempts should appear on the first page.
        self.assertEqual(len(response.data["results"]), 5)

        # A next page should be available.
        self.assertIsNotNone(response.data["next"])

    def test_attempt_history_returns_second_page(self):
        self.client.force_authenticate(user=self.student)

        # Create six additional attempts.
        for index in range(6):
            QuizAttempt.objects.create(
                student=self.student,
                quiz=self.quiz,
                score=80,
                passed=True,
            )

        url = reverse("quiz-attempt-history")
        response = self.client.get(url, {"page": 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    def test_attempt_history_returns_error_for_invalid_page(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("quiz-attempt-history")
        response = self.client.get(url, {"page": 999})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QuizSubmissionAPITests(APITestCase):

    def setUp(self):
        # Create a student.
        self.student = User.objects.create_user(
            username="quiz_student",
            email="quizstudent@example.com",
            password="testpass123",
            role="STUDENT",
        )

        # Create an instructor.
        self.instructor = User.objects.create_user(
            username="quiz_instructor",
            email="quizinstructor@example.com",
            password="testpass123",
            role="INSTRUCTOR",
        )

        # Create a published course.
        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Python API Course",
            slug="python-api-course",
            description="A course for testing quiz submission.",
            level="BEGINNER",
            is_free=True,
            price=0,
            is_published=True,
        )

        # Create a section.
        self.section = Section.objects.create(
            course=self.course,
            title="Python Basics",
            order=1,
        )

        # Create a lesson.
        self.lesson = Lesson.objects.create(
            section=self.section,
            title="Python Functions",
            content_type="TEXT",
            text_content="Functions are reusable blocks of code.",
            duration_minutes=10,
            order=1,
        )

        # Create a quiz.
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title="Python Functions Quiz",
            passing_score=70,
        )

        # Create a question.
        self.question = Question.objects.create(
            quiz=self.quiz,
            text="Which keyword defines a function in Python?",
            order=1,
        )

        # Create the correct choice.
        self.correct_choice = Choice.objects.create(
            question=self.question,
            text="def",
            is_correct=True,
        )

        # Create an incorrect choice.
        self.incorrect_choice = Choice.objects.create(
            question=self.question,
            text="classify",
            is_correct=False,
        )

        # Enroll the student and grant course access.
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

    def test_student_submits_correct_answer_and_passes(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("api_quiz_submit", kwargs={"quiz_id": self.quiz.id})

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["correct_answers"], 1)
        self.assertEqual(response.data["total_questions"], 1)
        self.assertEqual(response.data["score"], 100)
        self.assertEqual(response.data["passing_score"], 70)
        self.assertTrue(response.data["passed"])

        self.assertEqual(QuizAttempt.objects.count(), 1)
        self.assertEqual(QuizAnswer.objects.count(), 1)

    def test_student_submits_incorrect_answer_and_fails(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.incorrect_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["correct_answers"], 0)
        self.assertEqual(response.data["total_questions"], 1)
        self.assertEqual(response.data["score"], 0)
        self.assertEqual(response.data["passing_score"], 70)
        self.assertFalse(response.data["passed"])

        self.assertEqual(QuizAttempt.objects.count(), 1)
        self.assertEqual(QuizAnswer.objects.count(), 1)

    def test_unauthenticated_user_cannot_submit_quiz(self):
        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_instructor_cannot_submit_quiz(self):
        self.client.force_authenticate(user=self.instructor)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_submission_rejects_choice_from_another_question(self):
        self.client.force_authenticate(user=self.student)

        # Create another question in the same quiz.
        another_question = Question.objects.create(
            quiz=self.quiz,
            text="What is Python?",
            order=2,
        )

        # Create a choice that belongs to the other question.
        another_choice = Choice.objects.create(
            question=another_question,
            text="A programming language",
            is_correct=True,
        )

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": another_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # Invalid submissions must not create attempts or answers.
        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_submission_rejects_unanswered_questions(self):
        self.client.force_authenticate(user=self.student)

        # Create a second question.
        second_question = Question.objects.create(
            quiz=self.quiz,
            text="What is Python?",
            order=2,
        )

        Choice.objects.create(
            question=second_question,
            text="A programming language",
            is_correct=True,
        )

        Choice.objects.create(
            question=second_question,
            text="A database",
            is_correct=False,
        )

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        # Submit an answer for only the first question.
        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_submission_rejects_duplicate_answers_for_same_question(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                },
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.incorrect_choice.id,
                },
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_submission_rejects_question_from_another_quiz(self):
        self.client.force_authenticate(user=self.student)

        # Create another lesson and quiz.
        another_lesson = Lesson.objects.create(
            section=self.section,
            title="Advanced Python",
            content_type="TEXT",
            text_content="Advanced Python concepts.",
            duration_minutes=15,
            order=2,
        )

        another_quiz = Quiz.objects.create(
            lesson=another_lesson,
            title="Advanced Python Quiz",
            passing_score=70,
        )

        # Create a question and choice belonging to the other quiz.
        another_question = Question.objects.create(
            quiz=another_quiz,
            text="Which data structure stores key-value pairs?",
            order=1,
        )

        another_choice = Choice.objects.create(
            question=another_question,
            text="Dictionary",
            is_correct=True,
        )

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": another_question.id,
                    "selected_choice_id": another_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_student_without_enrollment_cannot_submit_quiz(self):
        unenrolled_student = User.objects.create_user(
            username="unenrolled_student",
            email="unenrolled@example.com",
            password="testpass123",
            role="STUDENT",
        )

        self.client.force_authenticate(user=unenrolled_student)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_student_with_unpaid_enrollment_cannot_submit_quiz(self):
        # Change the course to paid.
        self.course.is_free = False
        self.course.price = 1000
        self.course.save()

        # Mark the student's enrollment as unpaid.
        enrollment = Enrollment.objects.get(
            student=self.student,
            course=self.course,
        )
        enrollment.has_paid = False
        enrollment.save()

        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_submission_rejects_empty_answers(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": self.quiz.id},
        )

        payload = {"answers": []}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_submission_returns_404_for_nonexistent_quiz(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_submit",
            kwargs={"quiz_id": 999999},
        )

        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "selected_choice_id": self.correct_choice.id,
                }
            ]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(QuizAttempt.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)


class QuizDetailAPITests(APITestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username="detail_student",
            email="detailstudent@example.com",
            password="testpass123",
            role="STUDENT",
        )

        self.instructor = User.objects.create_user(
            username="detail_instructor",
            email="detailinstructor@example.com",
            password="testpass123",
            role="INSTRUCTOR",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            title="Django API Course",
            slug="django-api-course",
            description="A course for testing the quiz detail API.",
            level="BEGINNER",
            is_free=True,
            price=0,
            is_published=True,
        )

        self.section = Section.objects.create(
            course=self.course,
            title="Django Basics",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            section=self.section,
            title="Django REST Framework",
            content_type="TEXT",
            text_content="Learn to build APIs with Django REST Framework.",
            duration_minutes=10,
            order=1,
        )

        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title="Django API Quiz",
            passing_score=70,
        )

        self.question = Question.objects.create(
            quiz=self.quiz,
            text="Which framework extends Django for REST APIs?",
            order=1,
        )

        self.correct_choice = Choice.objects.create(
            question=self.question,
            text="Django REST Framework",
            is_correct=True,
        )

        self.incorrect_choice = Choice.objects.create(
            question=self.question,
            text="Flask",
            is_correct=False,
        )

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            has_paid=True,
        )

    def test_enrolled_student_can_retrieve_quiz_details(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_detail",
            kwargs={"quiz_id": self.quiz.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_unauthenticated_user_cannot_retrieve_quiz_details(self):
        url = reverse(
            "api_quiz_detail",
            kwargs={"quiz_id": self.quiz.id},
        )

        response = self.client.get(url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_instructor_cannot_retrieve_quiz_details(self):
        self.client.force_authenticate(user=self.instructor)

        url = reverse(
            "api_quiz_detail",
            kwargs={"quiz_id": self.quiz.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unenrolled_student_cannot_retrieve_quiz_details(self):
        unenrolled_student = User.objects.create_user(
            username="detail_unenrolled",
            email="detailunenrolled@example.com",
            password="testpass123",
            role="STUDENT",
        )

        self.client.force_authenticate(user=unenrolled_student)

        url = reverse(
            "api_quiz_detail",
            kwargs={"quiz_id": self.quiz.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_quiz_details_do_not_expose_correct_answers(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_detail",
            kwargs={"quiz_id": self.quiz.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        # Check the serialized response doesn't reveal answer correctness.
        response_text = str(response.data).lower()

        self.assertNotIn("is_correct", response_text)
        self.assertNotIn("correct_answer", response_text)

    def test_quiz_details_do_not_expose_correct_answers(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "api_quiz_detail",
            kwargs={"quiz_id": self.quiz.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_text = str(response.data).lower()

        self.assertNotIn("is_correct", response_text)
        self.assertNotIn("correct_answer", response_text)

        # Confirm that the expected choices are still available.
        self.assertIn("django rest framework", response_text)
        self.assertIn("flask", response_text)
