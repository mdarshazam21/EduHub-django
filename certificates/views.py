import uuid
from django.core.exceptions import PermissionDenied
from accounts.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from courses.models import Course, Lesson, Enrollment
from progress.models import LessonProgress
from quizzes.models import Quiz, QuizAttempt
from .models import Certificate
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def is_course_complete(student, course):
    # Get all lessons belonging to this course.
    lessons = Lesson.objects.filter(section__course=course)

    # Count the total lessons.
    total_lessons = lessons.count()

    # A course with no lessons cannot be completed.
    if total_lessons == 0:
        return False

    # Count completed lessons belonging to this course.
    completed_lessons = LessonProgress.objects.filter(
        student=student,
        lesson__in=lessons,
    ).count()

    # Every lesson must be completed.
    if completed_lessons < total_lessons:
        return False

    # Every quiz attached to a lesson must have a passing attempt.
    quizzes = Quiz.objects.filter(lesson__in=lessons)

    for quiz in quizzes:
        passed_quiz = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz,
            passed=True,
        ).exists()

        if not passed_quiz:
            return False

    # All lessons and required quizzes are complete.
    return True


@login_required
def generate_certificate(request, slug):
    # Only students can request course certificates.
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students can receive course certificates.")

    course = get_object_or_404(Course, slug=slug, is_published=True)

    # Only enrolled students with confirmed access can request a certificate.
    enrollment = Enrollment.objects.filter(
        student=request.user, course=course, has_paid=True
    ).first()

    if enrollment is None:
        messages.error(
            request, "You must be enrolled in this course to receive a certificate."
        )
        return redirect("course_detail", slug=course.slug)

    # Verify that the course requirements have been completed.
    if not is_course_complete(request.user, course):
        messages.error(
            request,
            "Complete all lessons and required quizzes before requesting your certificate.",
        )
        return redirect("course_detail", slug=course.slug)

    certificate, created = Certificate.objects.get_or_create(
        student=request.user, course=course
    )

    if created:
        messages.success(
            request, "Congratulations! Your certificate has been generated."
        )
    else:
        messages.info(
            request, "You have already received a certificate for this course."
        )

    return redirect("view_certificate", certificate_id=certificate.certificate_id)


@login_required
def view_certificate(request, certificate_id):
    certificate = get_object_or_404(
        Certificate.objects.select_related("student", "course"),
        certificate_id=certificate_id,
        student=request.user,
    )

    return render(
        request,
        "certificates/certificate.html",
        {"certificate": certificate},
    )


@login_required
def download_certificate(request, certificate_id):
    certificate = get_object_or_404(
        Certificate.objects.select_related("student", "course"),
        certificate_id=certificate_id,
        student=request.user,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="EduHub_Certificate_{certificate.certificate_id}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)

    # White background with a decorative border.
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setStrokeColor(colors.HexColor("#1E3A8A"))
    pdf.setLineWidth(4)
    pdf.rect(25, 25, width - 50, height - 50, fill=0, stroke=1)

    pdf.setStrokeColor(colors.HexColor("#D4AF37"))
    pdf.setLineWidth(1.5)
    pdf.rect(35, 35, width - 70, height - 70, fill=0, stroke=1)

    # Certificate heading.
    pdf.setFillColor(colors.HexColor("#1E3A8A"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(
        width / 2,
        height - 100,
        "CERTIFICATE OF COMPLETION",
    )

    # Decorative divider.
    pdf.setStrokeColor(colors.HexColor("#D4AF37"))
    pdf.setLineWidth(2)
    pdf.line(width / 2 - 120, height - 120, width / 2 + 120, height - 120)

    pdf.setFillColor(colors.HexColor("#555555"))
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(
        width / 2,
        height - 165,
        "This certificate is proudly presented to",
    )

    # Student name.
    student_name = certificate.student.get_full_name() or certificate.student.username

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawCentredString(
        width / 2,
        height - 210,
        student_name,
    )

    # Course completion text.
    pdf.setFillColor(colors.HexColor("#555555"))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(
        width / 2,
        height - 250,
        "for successfully completing the course",
    )

    # Course title.
    pdf.setFillColor(colors.HexColor("#1E3A8A"))
    pdf.setFont("Helvetica-Bold", 21)
    pdf.drawCentredString(
        width / 2,
        height - 285,
        certificate.course.title[:70],
    )

    # Issue date.
    pdf.setFillColor(colors.HexColor("#555555"))
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        width / 2,
        height - 325,
        f"Issued on: {certificate.issued_at.strftime('%B %d, %Y')}",
    )

    # Certificate ID.
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(
        width / 2,
        65,
        f"Certificate ID: {certificate.certificate_id}",
    )

    pdf.save()

    return response


def verify_certificate(request):
    certificate = None
    searched = False

    if request.method == "POST":
        certificate_id = request.POST.get("certificate_id", "").strip()
        searched = True

        if certificate_id:
            try:
                certificate = (
                    Certificate.objects.select_related("student", "course")
                    .filter(certificate_id=certificate_id)
                    .first()
                )
            except (ValueError, TypeError):
                certificate = None

    return render(
        request,
        "certificates/verify_certificate.html",
        {
            "certificate": certificate,
            "searched": searched,
        },
    )
