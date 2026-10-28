from django import forms
from .models import Review, Course, Section, Lesson


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)]
            )
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "level",
            "is_free",
            "price",
            "thumbnail",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "level": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


# Form for creating and editing course sections
class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ["title", "order"]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter section title"}
            ),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


# Form for creating and editing lessons
class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "content_type",
            "video_file",
            "text_content",
            "duration_minutes",
            "order",
            "is_preview",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter lesson title"}
            ),
            "content_type": forms.Select(attrs={"class": "form-select"}),
            "text_content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Enter lesson content",
                }
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }
