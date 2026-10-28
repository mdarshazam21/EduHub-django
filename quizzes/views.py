from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db import transaction

from courses.models import Enrollment
from .models import Quiz, Choice, QuizAttempt, QuizAnswer

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView

from .serializers import QuizAttemptSerializer
from .serializers import QuizSerializer, QuizSubmissionSerializer
from rest_framework.exceptions import ValidationError


@login_required
def take_quiz(request, quiz_id):

    # Find the quiz.
    quiz = get_object_or_404(
        Quiz.objects.select_related("lesson__section__course"), pk=quiz_id
    )

    # Find the course associated with the quiz.
    course = quiz.lesson.section.course

    # Only students can take quizzes.
    if request.user.role != "STUDENT":
        raise PermissionDenied("Only students can take quizzes.")

    # Verify that the student has access to the course.
    is_enrolled = Enrollment.objects.filter(
        student=request.user, course=course, has_paid=True
    ).exists()

    if not is_enrolled:
        raise PermissionDenied("You must enroll in this course to take this quiz.")

    # Fetch the questions in their configured order.
    questions = list(quiz.questions.prefetch_related("choices").all())

    # Prevent attempts on an empty quiz.
    if not questions:
        messages.error(request, "This quiz does not have any questions yet.")

        return redirect("course_detail", slug=course.slug)

    # Process the submitted answers.
    if request.method == "POST":

        submitted_answers = {}
        correct_count = 0

        # Validate every answer before creating the attempt.
        for question in questions:

            selected_choice_id = request.POST.get(f"question_{question.id}")

            # Every question must have an answer.
            if not selected_choice_id:
                messages.error(
                    request, "Please answer every question before submitting."
                )

                return render(
                    request,
                    "quizzes/take_quiz.html",
                    {
                        "quiz": quiz,
                        "questions": questions,
                    },
                    status=400,
                )

            # The selected choice must belong to this question.
            selected_choice = get_object_or_404(
                Choice, pk=selected_choice_id, question=question
            )

            submitted_answers[question.id] = selected_choice

            if selected_choice.is_correct:
                correct_count += 1

        # Calculate the percentage score.
        total_questions = len(questions)

        score = round((correct_count / total_questions) * 100)

        passed = score >= quiz.passing_score

        # Save the attempt and its answers together.
        with transaction.atomic():

            attempt = QuizAttempt.objects.create(
                student=request.user, quiz=quiz, score=score, passed=passed
            )

            QuizAnswer.objects.bulk_create(
                [
                    QuizAnswer(
                        attempt=attempt,
                        question=question,
                        selected_choice=submitted_answers[question.id],
                    )
                    for question in questions
                ]
            )

        messages.success(request, f"Quiz submitted! You scored {score}%.")

        return redirect("quiz_result", attempt_id=attempt.id)

    # Display the quiz form.
    return render(
        request,
        "quizzes/take_quiz.html",
        {
            "quiz": quiz,
            "questions": questions,
        },
    )


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, student=request.user)

    answers = attempt.answers.select_related("question", "selected_choice")

    return render(
        request,
        "quizzes/quiz_result.html",
        {
            "attempt": attempt,
            "answers": answers,
        },
    )


class QuizDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        # Only students can access quizzes.
        if request.user.role != "STUDENT":
            return Response(
                {"error": "Only students can access quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Find the quiz and its related course.
        quiz = get_object_or_404(
            Quiz.objects.select_related("lesson__section__course").prefetch_related(
                "questions__choices"
            ),
            pk=quiz_id,
        )

        # Find the course associated with the quiz.
        course = quiz.lesson.section.course

        # Check whether the student is enrolled.
        is_enrolled = Enrollment.objects.filter(
            student=request.user,
            course=course,
            has_paid=True,
        ).exists()

        if not is_enrolled:
            return Response(
                {"error": "You must enroll in this course to access this quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Serialize the quiz without revealing correct answers.
        serializer = QuizSerializer(quiz)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class QuizSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        # 1. Only students can submit quizzes.
        if request.user.role != "STUDENT":
            return Response(
                {"error": "Only students can submit quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Find the quiz and its related course.
        quiz = get_object_or_404(
            Quiz.objects.select_related("lesson__section__course").prefetch_related(
                "questions__choices"
            ),
            pk=quiz_id,
        )

        course = quiz.lesson.section.course

        # 3. Verify enrollment and payment.
        is_enrolled = Enrollment.objects.filter(
            student=request.user,
            course=course,
            has_paid=True,
        ).exists()

        if not is_enrolled:
            return Response(
                {"error": "You must enroll in this course to submit the quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Get all quiz questions.
        questions = list(quiz.questions.all())

        if not questions:
            return Response(
                {"error": "This quiz has no questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5. Validate the request structure.
        serializer = QuizSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submitted_answers = serializer.validated_data["answers"]

        # 6. Make sure every quiz question is answered exactly once.
        question_map = {question.id: question for question in questions}
        submitted_question_ids = {answer["question_id"] for answer in submitted_answers}

        if submitted_question_ids != set(question_map.keys()):
            return Response(
                {
                    "error": (
                        "You must answer every question in this quiz "
                        "and must not submit unrelated questions."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 7. Validate each selected choice and calculate correct answers.
        selected_answers = {}
        correct_count = 0

        for answer in submitted_answers:
            question_id = answer["question_id"]
            choice_id = answer["selected_choice_id"]

            question = question_map[question_id]

            choice = next(
                (choice for choice in question.choices.all() if choice.id == choice_id),
                None,
            )

            if choice is None:
                return Response(
                    {
                        "error": (
                            f"Choice {choice_id} does not belong "
                            f"to question {question_id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            selected_answers[question_id] = choice

            if choice.is_correct:
                correct_count += 1

        # 8. Calculate the score and passing status.
        total_questions = len(questions)
        score = round((correct_count / total_questions) * 100)
        passed = score >= quiz.passing_score

        # 9. Save the attempt and answers together.
        with transaction.atomic():
            attempt = QuizAttempt.objects.create(
                student=request.user,
                quiz=quiz,
                score=score,
                passed=passed,
            )

            QuizAnswer.objects.bulk_create(
                [
                    QuizAnswer(
                        attempt=attempt,
                        question=question,
                        selected_choice=selected_answers[question.id],
                    )
                    for question in questions
                ]
            )

        # 10. Return the result.
        return Response(
            {
                "message": "Quiz submitted successfully.",
                "attempt_id": attempt.id,
                "quiz_title": quiz.title,
                "correct_answers": correct_count,
                "total_questions": total_questions,
                "score": score,
                "passing_score": quiz.passing_score,
                "passed": passed,
                "attempted_at": attempt.attempted_at,
            },
            status=status.HTTP_201_CREATED,
        )


class QuizAttemptDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id):
        # Only students can access quiz attempt results.
        if request.user.role != "STUDENT":
            return Response(
                {"error": "Only students can access quiz results."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve only the attempt belonging to the logged-in student.
        attempt = get_object_or_404(
            QuizAttempt.objects.select_related("quiz"),
            pk=attempt_id,
            student=request.user,
        )

        # Convert the attempt into JSON.
        serializer = QuizAttemptSerializer(attempt)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class QuizAttemptHistoryAPIView(ListAPIView):
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != "STUDENT":
            return QuizAttempt.objects.none()

        queryset = (
            QuizAttempt.objects.filter(student=self.request.user)
            .select_related("quiz")
            .order_by("-attempted_at")
        )

        quiz_id = self.request.query_params.get("quiz_id")

        if quiz_id:
            try:
                quiz_id = int(quiz_id)
            except ValueError:
                raise ValidationError(
                    {"quiz_id": "Quiz ID must be a positive integer."}
                )

            if quiz_id <= 0:
                raise ValidationError(
                    {"quiz_id": "Quiz ID must be a positive integer."}
                )

            queryset = queryset.filter(quiz_id=quiz_id)

        return queryset

