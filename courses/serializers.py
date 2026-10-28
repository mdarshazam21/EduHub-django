from rest_framework import serializers
from .models import Course, Enrollment, Review
from django.db.models import Avg, Count


class CourseSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    rating_distribution = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "price",
            "average_rating",
            "total_reviews",
            "rating_distribution",
        ]

    def get_average_rating(self, obj):
        result = obj.reviews.aggregate(average=Avg("rating"))["average"]

        return round(result, 2) if result is not None else 0

    def get_total_reviews(self, obj):
        return obj.reviews.count()

    def get_rating_distribution(self, obj):
        distribution = obj.reviews.values("rating").annotate(total=Count("id"))

        result = {str(rating): 0 for rating in range(1, 6)}

        for item in distribution:
            result[str(item["rating"])] = item["total"]

        return result


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "course",
            "course_title",
            "enrolled_at",
            "has_paid",
        ]
        read_only_fields = [
            "id",
            "course",
            "course_title",
            "enrolled_at",
            "has_paid",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source="student.username",
        read_only=True,
    )

    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "student",
            "student_username",
            "course",
            "course_title",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "student_username",
            "course",
            "course_title",
            "created_at",
            "updated_at",
        ]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
