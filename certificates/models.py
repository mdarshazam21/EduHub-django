import uuid

from django.conf import settings
from django.db import models

from courses.models import Course


class Certificate(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates"
    )

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="certificates"
    )

    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"
