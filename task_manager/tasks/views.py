# tasks/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as django_login, logout as django_logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .forms import TaskForm, CustomUserCreationForm
from .models import Task, CustomUser, EmailTemplate
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .permissions import IsAdminHODSupervisorOrAssigned
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .pagination import TaskLimitOffsetPagination

# DRF & Auth
from rest_framework.authtoken.models import Token
from rest_framework import viewsets, permissions, filters
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    TaskSerializer,
    EmailTemplateSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ------------------ HTML VIEWS ------------------

def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.email:
                send_mail(
                    "Welcome to Task Manager!",
                    f"Hi {user.username}, welcome to Task Manager!",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            django_login(request, user)
            return redirect("dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, "tasks/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            django_login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "tasks/login.html")


def logout_view(request):
    django_logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    tasks = get_tasks_for_user(request.user)
    return render(request, "tasks/dashboard.html", {"tasks": tasks, "filter": "all"})


@login_required
def completed_tasks(request):
    tasks = get_tasks_for_user(request.user, completed=True)
    return render(request, "tasks/dashboard.html", {"tasks": tasks, "filter": "completed"})


@login_required
def pending_tasks(request):
    tasks = get_tasks_for_user(request.user, completed=False)
    return render(request, "tasks/dashboard.html", {"tasks": tasks, "filter": "pending"})


def get_tasks_for_user(user, completed=None):
    if getattr(user, "role", "") == "admin" or user.is_staff:
        qs = Task.objects.all()
    elif getattr(user, "role", "") == "hod":
        qs = Task.objects.filter(user__role="supervisor")
    elif getattr(user, "role", "") == "supervisor":
        qs = (Task.objects.filter(user=user) | Task.objects.filter(user__role="operator")).distinct()
    else:
        qs = Task.objects.filter(user=user)

    if completed is True:
        qs = qs.filter(completed=True)
    elif completed is False:
        qs = qs.filter(completed=False)

    return qs


@login_required
def task_create(request):
    user = request.user

    if user.role not in ["admin", "hod", "supervisor"]:
        return HttpResponseForbidden("You are not allowed to create tasks.")

    if user.role == "admin":
        assignable_users = User.objects.all()
    elif user.role == "hod":
        assignable_users = User.objects.filter(role__in=["supervisor", "operator"])
    else:  # supervisor
        assignable_users = User.objects.filter(role="operator")

    if request.method == "POST":
        form = TaskForm(request.POST)
        form.fields['recipients'].queryset = assignable_users

        if form.is_valid():
            recipients = form.cleaned_data.get("recipients")
            if not recipients:
                task = form.save(commit=False)
                task.user = user
                task.save()
            else:
                for recipient in recipients:
                    task = form.save(commit=False)
                    task.user = recipient
                    task.pk = None
                    task.save()

            messages.success(request, "Task assigned successfully.")
            return redirect("dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TaskForm()
        form.fields['recipients'].queryset = assignable_users

    email_templates = EmailTemplate.objects.all()
    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "users": assignable_users,
            "email_templates": email_templates,
            "allowed_roles_for_email": ["admin", "hod", "supervisor"],
        },
    )


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, id=pk)
    user = request.user

    if user.role == "admin":
        pass
    elif user.role in ["hod", "supervisor"]:
        if user != task.user and user not in task.assigned_to.all():
            return HttpResponseForbidden("You cannot edit this task.")
    elif user.role == "user":
        if user != task.user and user not in task.assigned_to.all():
            return HttpResponseForbidden("You cannot edit this task.")

    if user.role == "admin":
        assignable_users = User.objects.all()
    elif user.role == "hod":
        assignable_users = User.objects.filter(role="supervisor")
    elif user.role == "supervisor":
        assignable_users = User.objects.filter(role="hod")
    else:
        assignable_users = User.objects.filter(id=task.user.id)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, user=user)
        form.fields['recipients'].queryset = assignable_users

        if "update_task" in request.POST:
            if form.is_valid():
                recipients = form.cleaned_data.get("recipients")
                if recipients:
                    for recipient in recipients:
                        if recipient != task.user:
                            new_task = form.save(commit=False)
                            new_task.user = recipient
                            new_task.pk = None
                            new_task.save()
                else:
                    form.save()
                messages.success(request, "Task updated successfully.")
                return redirect("dashboard")
            else:
                messages.error(request, "Please correct the errors below.")

        elif "send_email" in request.POST:
            if user.role not in ["admin", "hod", "supervisor"]:
                return HttpResponseForbidden("You are not allowed to send emails.")

            recipient_ids = request.POST.getlist("recipients")
            recipients = User.objects.filter(id__in=recipient_ids, email__isnull=False)
            recipient_emails = [r.email for r in recipients if r.email]

            if not recipient_emails:
                messages.error(request, "No valid recipient emails selected.")
                return redirect("task_edit", pk=pk)

            template_id = request.POST.get("email_template")
            if template_id:
                try:
                    template = EmailTemplate.objects.get(id=template_id)
                    subject = template.subject
                    message = template.body
                except EmailTemplate.DoesNotExist:
                    subject = request.POST.get("custom_subject") or f"Task Reminder: {task.title}"
                    message = request.POST.get("custom_message", "")
            else:
                subject = request.POST.get("custom_subject") or f"Task Reminder: {task.title}"
                message = request.POST.get("custom_message", "")

            html_content = render_to_string(
                "tasks/emails/task_due_soon.html",
                {"user": user, "task": task, "custom_message": message},
            )

            email = EmailMultiAlternatives(
                subject,
                message or html_content,
                settings.DEFAULT_FROM_EMAIL,
                recipient_emails,
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            messages.success(request, f"📧 Email sent to: {', '.join(recipient_emails)}")
            return redirect("task_edit", pk=pk)

    else:
        form = TaskForm(instance=task, user=user)
        form.fields['recipients'].queryset = assignable_users

    email_templates = EmailTemplate.objects.all()
    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "task": task,
            "users": assignable_users,
            "email_templates": email_templates,
            "allowed_roles_for_email": ["admin", "hod", "supervisor"],
        },
    )


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, id=pk)
    user = request.user

    if user.role == "hod":
        return HttpResponseForbidden("HOD cannot delete tasks.")
    if user.role == "supervisor" and task.user.role not in ["operator", "supervisor"]:
        return HttpResponseForbidden("Supervisor can only delete their own or operator tasks.")
    if user.role in ["operator", "user"] and task.user != user:
        return HttpResponseForbidden("You cannot delete this task.")

    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted successfully.")
        return redirect("dashboard")

    return render(request, "tasks/task_confirm_delete.html", {"task": task})


# ------------------ DRF API VIEWS ------------------



from django.core.mail import EmailMultiAlternatives
from django.conf import settings

# ------------------ Task List & Create API ------------------
class TaskListAPIView(generics.ListAPIView):
    queryset = Task.objects.all().order_by('-created_at')
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]  # Django Filter
    filterset_fields = ['completed', 'assigned_to', 'completed_by', 'user']  # must be real model fields
    pagination_class = TaskLimitOffsetPagination

class TaskListCreateAPI(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskLimitOffsetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.select_related('user').prefetch_related('assigned_to')

        # === ROLE-BASED VISIBILITY ONLY ===
        if user.is_staff or user.role == "admin":
            role_queryset = queryset
        elif user.role in ["hod", "supervisor"]:
            role_queryset = queryset.filter(Q(assigned_to=user) | Q(user=user)).distinct()
        else:  # normal user
            role_queryset = queryset.filter(assigned_to=user)

        # --- STORE COUNTS BEFORE QUERY PARAM FILTERING ---
        self.total_count = role_queryset.count()
        self.pending_count = role_queryset.filter(status='pending').count()
        self.completed_count = role_queryset.filter(status='completed').count()

        # === APPLY QUERY PARAM FILTERS ===
        status = self.request.query_params.get("status")
        if status:
            role_queryset = role_queryset.filter(status__iexact=status)

        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            role_queryset = role_queryset.filter(assigned_to__id=assigned_to)

        created_by = self.request.query_params.get("user")
        if created_by:
            role_queryset = role_queryset.filter(user__id=created_by)

        completed_by = self.request.query_params.get("completed_by")
        if completed_by:
            role_queryset = role_queryset.filter(completed_by__id=completed_by)

        return role_queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Add counts to response
        response.data['total_count'] = self.total_count
        response.data['pending_count'] = self.pending_count
        response.data['completed_count'] = self.completed_count
        return response

    def perform_create(self, serializer):
        user = self.request.user
        assigned_ids = self.request.data.get("assigned_to_ids", [])
        assigned_users = list(User.objects.filter(id__in=assigned_ids)) if assigned_ids else []

        # === ROLE VALIDATION ===
        if user.role == "hod":
            for u in assigned_users:
                if u.role != "user":
                    raise PermissionDenied("HOD can only assign tasks to users.")
        elif user.role == "supervisor":
            for u in assigned_users:
                if u != user and u.role not in ["hod", "user"]:
                    raise PermissionDenied("Supervisor can only assign tasks to HOD or user.")
        elif user.role == "user":
            if assigned_users and any(u != user for u in assigned_users):
                raise PermissionDenied("Users can only assign tasks to themselves.")
        elif user.role not in ["admin", "supervisor", "hod", "user"]:
            raise PermissionDenied("Invalid role.")

        # === SAVE TASK ===
        serializer.save(user=user)

        # === ASSIGN USERS & SEND EMAIL ===
        if assigned_users:
            serializer.instance.assigned_to.set(assigned_users)
            subject = f"New Task Assigned: {serializer.instance.title}"
            html_content = f"""
            <html><body>
              <p>Hello,</p>
              <p>You have been assigned a new task by <strong>{user.username}</strong>.</p>
              <p><strong>Task:</strong> {serializer.instance.title}<br>
                 <strong>Description:</strong> {serializer.instance.description or 'No description'}<br>
                 <strong>Due Date:</strong> {serializer.instance.due_date or 'Not specified'}</p>
              <p>Login to your dashboard for details.</p>
            </body></html>
            """
            recipient_emails = [u.email for u in assigned_users if u.email]
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@taskmanager.local")
            if recipient_emails:
                try:
                    email = EmailMultiAlternatives(subject, "", from_email, recipient_emails)
                    email.attach_alternative(html_content, "text/html")
                    email.send(fail_silently=True)
                except Exception as e:
                    print(f"Email send error: {e}")

# ------------------ Task Detail API ------------------
class TaskDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminHODSupervisorOrAssigned]

    def perform_update(self, serializer):
        user = self.request.user
        assigned_ids = self.request.data.get("assigned_to_ids", [])
        assigned_users = list(User.objects.filter(id__in=assigned_ids)) if assigned_ids else []

        # Track previous states
        prev_completed = serializer.instance.completed
        prev_title = serializer.instance.title
        prev_description = serializer.instance.description
        prev_due_date = serializer.instance.due_date

        # Role-based validation and save
        if user.role == "admin":
            serializer.save()
        elif user.role == "hod":
            if serializer.instance.user != user and user not in serializer.instance.assigned_to.all():
                raise PermissionDenied("HOD cannot edit this task.")
            serializer.save()
        elif user.role == "supervisor":
            if serializer.instance.user != user and user not in serializer.instance.assigned_to.all():
                raise PermissionDenied("Supervisor cannot edit this task.")
            for u in assigned_users:
                if u != user and u.role not in ["hod", "user"]:
                    raise PermissionDenied("Supervisor can only assign tasks to HOD or user.")
            serializer.save()
        elif user.role == "user":
            if serializer.instance.user != user and user not in serializer.instance.assigned_to.all():
                raise PermissionDenied("You cannot update this task.")
            if assigned_users and any(u != user for u in assigned_users):
                raise PermissionDenied("Users can only assign tasks to themselves.")
            serializer.save()
        else:
            raise PermissionDenied("Invalid role.")

        # Update assigned users if provided
        if assigned_users:
            serializer.instance.assigned_to.set(assigned_users)

        # Send HTML email to assigned users if task details changed
        if user.role in ["admin", "supervisor"] and (
            prev_title != serializer.instance.title or
            prev_description != serializer.instance.description or
            prev_due_date != serializer.instance.due_date
        ):
            assigned_emails = [u.email for u in serializer.instance.assigned_to.all() if u.email]
            if assigned_emails:
                subject = f"Task Updated: {serializer.instance.title}"
                html_content = f"""
<html>
  <body>
    <p>Hello,</p>
    <p>The task assigned to you has been updated by <strong>{user.username}</strong>.</p>
    <p><strong>Task:</strong> {serializer.instance.title}<br>
       <strong>Description:</strong> {serializer.instance.description or 'No description'}<br>
       <strong>Due Date:</strong> {serializer.instance.due_date or 'Not specified'}</p>
    <p>Please log in to your dashboard to view updated details.</p>
    <p>Regards,<br>Task Manager System</p>
  </body>
</html>
"""
                email = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, assigned_emails)
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=True)

        # Send HTML email to task creator if task is marked completed
        if not prev_completed and serializer.instance.completed:
            assigner = serializer.instance.user
            if assigner.email:
                subject = f"Task Completed: {serializer.instance.title}"
                html_content = f"""
<html>
  <body>
    <p>Hello {assigner.username},</p>
    <p>The task you assigned has been marked as completed by <strong>{user.username}</strong>.</p>
    <p><strong>Task:</strong> {serializer.instance.title}<br>
       <strong>Description:</strong> {serializer.instance.description or 'No description'}<br>
       <strong>Due Date:</strong> {serializer.instance.due_date or 'Not specified'}</p>
    <p>Please check your dashboard for details.</p>
    <p>Regards,<br>Task Manager System</p>
  </body>
</html>
"""
                email = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, [assigner.email])
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=True)


    def perform_destroy(self, instance):
        user = self.request.user
        if user.role == "admin":
            instance.delete()
        elif user.role in ["hod", "supervisor"] and (instance.user == user or instance.assigned_to.filter(id=user.id).exists()):
            instance.delete()
        elif user.role == "user" and instance.assigned_to.filter(id=user.id).exists():
            instance.delete()
        else:
            raise PermissionDenied("You don't have permission to delete this task")


# ------------------ EMAIL TEMPLATES ------------------

class EmailTemplateListAPI(generics.ListCreateAPIView):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmailTemplateDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class SendEmailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        subject = request.data.get("Subject")
        message = request.data.get("message")
        recipients = request.data.get("recipients", [])

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
            return Response({"success": f"📧 Email sent to {', '.join(recipients)}"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------ USER AUTH API ------------------

class UserRegistrationAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            resp = Response({
                "success": True,
                "message": "User registered successfully.",
                "user": UserSerializer(user).data,
                "token": token.key
            }, status=status.HTTP_201_CREATED)
            resp.set_cookie("auth_token", token.key, httponly=True, samesite="Lax")
            return resp
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        resp = Response({
            "success": True,
            "message": "Login successful.",
            "user": UserSerializer(user).data,
            "token": token.key,
            "role": user.role
        }, status=status.HTTP_200_OK)
        resp.set_cookie("auth_token", token.key, httponly=True, samesite="Lax")
        return resp


class LogoutAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token_key = None
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Token "):
            token_key = auth_header.split()[1]
        else:
            token_key = request.COOKIES.get("auth_token")

        if token_key:
            Token.objects.filter(key=token_key).delete()
        else:
            Token.objects.filter(user=request.user).delete()

        django_logout(request)
        resp = Response({"success": "Logged out successfully."})
        resp.delete_cookie("auth_token")
        return resp


class CurrentUserAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        user = request.user
        user.username = request.data.get("username", user.username)
        user.email = request.data.get("email", user.email)
        user.save()
        return Response(UserSerializer(user).data)


class AssignableUsersAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        users = User.objects.none()

        if user.role == "admin":
            users = User.objects.exclude(id=user.id)
        elif user.role == "hod":
            users = User.objects.filter(role="user")
        elif user.role == "supervisor":
            users = User.objects.filter(role__in=["hod"])
        data = [{"id": u.id, "username": u.username, "role": u.role} for u in users]
        return Response(data)


class EmployeeListAPI(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return User.objects.filter(role="employee")


class TaskFilterAPI(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        status_param = self.request.query_params.get("status", "all")

        if getattr(user, "role", "") == "admin":
            qs = Task.objects.all()
        elif getattr(user, "role", "") == "hod":
            qs = Task.objects.filter(user__role="supervisor")
        elif getattr(user, "role", "") == "supervisor":
            qs = (Task.objects.filter(user=user) | Task.objects.filter(user__role="operator")).distinct()
        else:
            qs = Task.objects.filter(user=user)

        if status_param == "completed":
            qs = qs.filter(completed=True)
        elif status_param == "pending":
            qs = qs.filter(completed=False)

        return qs

