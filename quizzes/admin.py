from django.contrib import admin

from .models import (
    Quiz,
    Question,
    Choice,
    QuizAttempt,
    QuizAnswer,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "lesson",
        "passing_score",
    )

    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "quiz",
        "order",
    )

    inlines = [ChoiceInline]


admin.site.register(Choice)
admin.site.register(QuizAttempt)
admin.site.register(QuizAnswer)
