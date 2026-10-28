from django.db import models
from django.conf import settings
from django.utils.text import slugify


# Define the Course model
class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_created",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
    )
    description = models.TextField()
    thumbnail = models.ImageField(upload_to="course_thumbnails/", blank=True, null=True)
    level = models.CharField(
        max_length=15, choices=Level.choices, default=Level.BEGINNER
    )
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# Define the Section model
class Section(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.title} — {self.title}"


# Define the Lesson model
class Lesson(models.Model):
    class ContentType(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        TEXT = "TEXT", "Text"

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=200)
    content_type = models.CharField(
        max_length=10, choices=ContentType.choices, default=ContentType.VIDEO
    )
    video_file = models.FileField(upload_to="lesson_videos/", blank=True, null=True)
    text_content = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.section.title} — {self.title}"


# Define the Resource model
class Resource(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="resources"
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="lesson_resources/")

    def __str__(self):
        return self.title


# Define the Enrollment model
class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    has_paid = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"


# Define the Review model
class Review(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_reviews",
    )

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField()

    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_review",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.username} — " f"{self.course.title} ({self.rating}/5)"
