# tasks/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import Task, EmailTemplate  # ✅ import models

CustomUser = get_user_model()  # ✅ just get the model, don't redefine it

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'role')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),  # add role field
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

    # Restrict "Admin" role assignment to superusers only
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "role" and not request.user.is_superuser:
            kwargs['choices'] = [
                (choice, label) for choice, label in db_field.choices if choice != "Admin"
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

admin.site.register(CustomUser, CustomUserAdmin)

# Task Admin
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description', 'user', 'role_of_user',
                    'created_at', 'updated_at', 'due_date', 'completed')
    search_fields = ('title', 'description', 'id', 'user__username')
    date_hierarchy = 'created_at'
    list_filter = ('created_at', 'updated_at', 'due_date', 'user', 'completed')

    def role_of_user(self, obj):
        return obj.user.role
    role_of_user.short_description = 'User Role'

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created_at')  # Example fields
    search_fields = ('subject',)