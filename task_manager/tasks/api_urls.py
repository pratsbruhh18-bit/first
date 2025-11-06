# tasks/api_urls.py
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import api_views

urlpatterns = [
    # Auth token endpoint
    path('auth/token/', obtain_auth_token, name='api-token-auth'),

    # Task APIs
    path('tasks/', api_views.TaskListCreateAPIView.as_view(), name='api-task-list'),
    path('tasks/<int:pk>/', api_views.TaskDetailAPIView.as_view(), name='api-task-detail'),

    # EmailTemplate APIs
    path('email-templates/', api_views.EmailTemplateListAPIView.as_view(), name='api-email-templates'),
    path('email-templates/<int:pk>/', api_views.EmailTemplateDetailAPIView.as_view(), name='api-email-template-detail'),
    path('employees/', api_views.EmployeeListAPI.as_view(), name='api_employees'),
]
