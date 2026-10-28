from django.db import models
from django.conf import settings
from courses.models import Lesson


class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=200)
    passing_score = models.PositiveIntegerField(default=70)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} — {self.quiz.title} ({self.score}%)"


class QuizAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="answers"
    )

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )

    selected_choice = models.ForeignKey(
        Choice, on_delete=models.CASCADE, related_name="selected_answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"], name="unique_question_per_quiz_attempt"
            )
        ]

    def __str__(self):
        return f"{self.question.text} → {self.selected_choice.text}"
