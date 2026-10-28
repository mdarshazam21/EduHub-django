from rest_framework import serializers
from .models import QuizAttempt
from .models import Quiz, Question, Choice


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "order", "choices"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "passing_score",
            "total_questions",
            "questions",
        ]

    def get_total_questions(self, quiz):
        return quiz.questions.count()


class QuizSubmissionSerializer(serializers.Serializer):
    answers = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_answers(self, answers):
        if not answers:
            raise serializers.ValidationError("You must submit answers for the quiz.")

        question_ids = []

        for answer in answers:
            if "question_id" not in answer:
                raise serializers.ValidationError(
                    "Every answer must include question_id."
                )

            if "selected_choice_id" not in answer:
                raise serializers.ValidationError(
                    "Every answer must include selected_choice_id."
                )

            question_id = answer["question_id"]
            choice_id = answer["selected_choice_id"]

            if not isinstance(question_id, int) or isinstance(question_id, bool):
                raise serializers.ValidationError("question_id must be an integer.")

            if not isinstance(choice_id, int) or isinstance(choice_id, bool):
                raise serializers.ValidationError(
                    "selected_choice_id must be an integer."
                )

            if question_id in question_ids:
                raise serializers.ValidationError(
                    "You cannot answer the same question more than once."
                )

            question_ids.append(question_id)

        return answers


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(
        source="quiz.title",
        read_only=True,
    )

    passing_score = serializers.IntegerField(
        source="quiz.passing_score",
        read_only=True,
    )

    correct_answers = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz_title",
            "score",
            "passing_score",
            "passed",
            "correct_answers",
            "total_questions",
            "attempted_at",
        ]

    def get_correct_answers(self, attempt):
        return attempt.answers.filter(
            selected_choice__is_correct=True
        ).count()

    def get_total_questions(self, attempt):
        return attempt.quiz.questions.count()

