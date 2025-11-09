from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import (
    TaskListCreateAPI,
    TaskDetailAPI,
    EmailTemplateListAPI,
    SendEmailAPI,
    UserRegistrationAPI,
    UserLoginAPI,
    AssignableUsersAPI,
    DepartmentViewSet,
    CustomTokenObtainPairView,
)

# ------------------------------------
# Router for ViewSets
# ------------------------------------
router = DefaultRouter()
router.register(r'api/departments', DepartmentViewSet, basename='department')

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
    path('api/tasks/', TaskListCreateAPI.as_view(), name='api_task_list_create'),
    path('api/tasks/<int:pk>/', TaskDetailAPI.as_view(), name='api_task_detail'),
    path('api/email-templates/', EmailTemplateListAPI.as_view(), name='api_email_templates'),
    path('api/send-email/', SendEmailAPI.as_view(), name='api_send_email'),
    path('api/register/', UserRegistrationAPI.as_view(), name='api_register'),
    path('api/login/', UserLoginAPI.as_view(), name='api_login'),
    path('api/employees/', views.EmployeeListAPI.as_view(), name='api_employees'),
    path('employee/', AssignableUsersAPI.as_view(), name='assignable-users'),

    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    # Department endpoints
    path('', include(router.urls)),  # 🔥 connects all ViewSets including departments
]
