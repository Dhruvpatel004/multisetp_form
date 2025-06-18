from django.contrib import admin

from .models import AdmissionApplication, College, Department


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ("name", "description")
    show_change_link = True


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "college")
    search_fields = ("name", "college__name")
    list_filter = ("college",)
    ordering = ("college", "name")


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "college", "created_at")
    search_fields = ("first_name", "last_name", "email")
    list_filter = ("college",)
    ordering = ("-created_at",)

    def college(self, obj):
        return obj.college.name if obj.college else "N/A"

    college.short_description = "College"
