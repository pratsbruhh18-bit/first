# tasks/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# -------------------------------
# Department Model
# -------------------------------
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# -------------------------------
# Custom User Model
# -------------------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("hod", "Head of Department"),
        ("supervisor", "Supervisor"),
        ("user", "User"),
    ]

    email = models.EmailField(unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default="user"
    )

    # 👇 Username-based login
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.role})"


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
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
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
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    # -------------------------------
    # Sub-task fields
    # -------------------------------
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subtasks'
    )
    task_number = models.CharField(max_length=50, blank=True)  # 1, 1.1, 1.2 etc.

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Sync status with completed
        if self.completed:
            self.status = "completed"
        elif self.status == "completed" and not self.completed:
            self.status = "pending"

        # Auto-generate task_number
        if self.parent:
            siblings_count = Task.objects.filter(parent=self.parent).exclude(id=self.id).count() + 1
            self.task_number = f"{self.parent.task_number}.{siblings_count}"
        else:
            if not self.task_number:
                top_level_count = Task.objects.filter(parent__isnull=True).exclude(id=self.id).count() + 1
                self.task_number = str(top_level_count)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_number} - {self.title}"


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
