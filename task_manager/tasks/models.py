# tasks/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# -------------------------------
# Custom User
# -------------------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("supervisor", "Supervisor"),
        ("hod", "Head of Department"),
        ("user", "User"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username


# -------------------------------
# Task Model
# -------------------------------
class Task(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tasks"
    )
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tasks",
        blank=True
    )
    completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_tasks"
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Sync status with completed
        if self.completed:
            self.status = "completed"
        elif self.status == "completed" and not self.completed:
            self.status = "pending"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title



# -------------------------------
# EmailTemplate Model
# -------------------------------
class EmailTemplate(models.Model):
    name = models.CharField(max_length=150)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
