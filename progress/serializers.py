from rest_framework import serializers

from courses.models import Enrollment, Lesson
from progress.models import LessonProgress


class DashboardCourseSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    completed_lessons = serializers.SerializerMethodField()
    remaining_lessons = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "course",
            "enrolled_at",
            "progress_percentage",
            "total_lessons",
            "completed_lessons",
            "remaining_lessons",
            "status",
        ]

    def _get_progress_data(self, enrollment):
        cache = self.context.setdefault("progress_cache", {})

        if enrollment.course_id not in cache:
            course = enrollment.course

            total_lessons = Lesson.objects.filter(section__course=course).count()

            completed_lessons = LessonProgress.objects.filter(
                student=enrollment.student,
                lesson__section__course=course,
            ).count()

            percentage = (
                round(completed_lessons / total_lessons * 100) if total_lessons else 0
            )

            cache[course.id] = {
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "progress_percentage": percentage,
            }

        return cache[enrollment.course_id]

    def get_total_lessons(self, enrollment):
        return self._get_progress_data(enrollment)["total_lessons"]

    def get_completed_lessons(self, enrollment):
        return self._get_progress_data(enrollment)["completed_lessons"]

    def get_remaining_lessons(self, enrollment):
        data = self._get_progress_data(enrollment)

        return data["total_lessons"] - data["completed_lessons"]

    def get_progress_percentage(self, enrollment):
        return self._get_progress_data(enrollment)["progress_percentage"]

    def get_status(self, enrollment):
        data = self._get_progress_data(enrollment)

        if data["total_lessons"] > 0 and (
            data["completed_lessons"] == data["total_lessons"]
        ):
            return "Completed"

        return "In Progress"


class StudentLessonProgressSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(
        source="section.title",
        read_only=True,
    )
    completed = serializers.SerializerMethodField()
    completed_at = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "section_title",
            "content_type",
            "duration_minutes",
            "order",
            "is_preview",
            "completed",
            "completed_at",
        ]

    def get_completed(self, lesson):
        student = self.context["student"]

        return LessonProgress.objects.filter(
            student=student,
            lesson=lesson,
        ).exists()

    def get_completed_at(self, lesson):
        student = self.context["student"]

        progress = LessonProgress.objects.filter(
            student=student,
            lesson=lesson,
        ).first()

        return progress.completed_at if progress else None
