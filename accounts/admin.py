from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "role",
                    "bio",
                    "profile_picture",
                )
            },
        ),
    )  # type: ignore

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "email",
                    "role",
                    "bio",
                    "profile_picture",
                )
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
    )
