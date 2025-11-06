from django.urls import path
from . import views
from .views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    TaskListCreateAPI,
    TaskDetailAPI,
    EmailTemplateListAPI,
    SendEmailAPI,
    UserRegistrationAPI,
    UserLoginAPI,
    AssignableUsersAPI,
)


urlpatterns = [
    # HTML Views
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('', views.dashboard, name='dashboard'),
    path('tasks/completed/', views.completed_tasks, name='completed_tasks'),
    path('tasks/pending/', views.pending_tasks, name='pending_tasks'),

    path('task/create/', views.task_create, name='task_create'),
    path('task/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:pk>/delete/', views.task_delete, name='task_delete'),

    # DRF API Views
    path('api/tasks/', views.TaskListCreateAPI.as_view(), name='api_task_list_create'),
    path('api/tasks/<int:pk>/', views.TaskDetailAPI.as_view(), name='api_task_detail'),
    path('api/email-templates/', views.EmailTemplateListAPI.as_view(), name='api_email_templates'),
    path('api/send-email/', views.SendEmailAPI.as_view(), name='api_send_email'),
    path('api/register/', UserRegistrationAPI.as_view(), name='api_register'),
    path('api/login/', UserLoginAPI.as_view(), name='api_login'),
    path('api/employees/', views.EmployeeListAPI.as_view(), name='api_employees'),
    path('employee/', AssignableUsersAPI.as_view(), name='assignable-users'),
    path("tasks/<int:pk>/", TaskDetailAPI.as_view(), name="task-detail"),

    #path('api/profile/', views.UserProfileAPI.as_view(), name='api_profile'),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

