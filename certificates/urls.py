from django.urls import path

from . import views

urlpatterns = [
    path(
        "generate/<slug:slug>/",
        views.generate_certificate,
        name="generate_certificate",
    ),
    path(
        "view/<uuid:certificate_id>/",
        views.view_certificate,
        name="view_certificate",
    ),
    path(
        "download/<uuid:certificate_id>/",
        views.download_certificate,
        name="download_certificate",
    ),
    path(
        "verify/",
        views.verify_certificate,
        name="verify_certificate",
    ),
]
