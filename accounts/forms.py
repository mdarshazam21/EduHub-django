from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    ROLE_CHOICES = (
        (User.Role.STUDENT, "Student"),
        (User.Role.INSTRUCTOR, "Instructor"),
    )

    role = forms.ChoiceField(choices=ROLE_CHOICES)
    email = forms.EmailField(required=True)

    class Meta:  # type: ignore
        model = User
        fields = [
            "username",
            "email",
            "role",
            "password1",
            "password2",
        ]
