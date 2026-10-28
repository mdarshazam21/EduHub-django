from django.contrib import admin
from .models import Course, Section, Lesson, Resource, Review
from .models import Enrollment


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "instructor", "level", "is_free", "price", "is_published"]
    list_filter = ["is_free", "is_published", "level"]
    search_fields = ["title", "description"]
    inlines = [SectionInline]


class SectionAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order"]
    inlines = [LessonInline]


admin.site.register(Course, CourseAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Lesson)
admin.site.register(Resource)
admin.site.register(Enrollment)
admin.site.register(Review)
