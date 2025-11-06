from rest_framework import generics, permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Task, EmailTemplate, CustomUser
from .serializers import TaskSerializer, EmailTemplateSerializer, UserSerializer


# --------------------------
# Task API Views
# --------------------------
class TaskListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # ✅ FIX: Ensure dashboard shows both created & assigned tasks (even self-assigned)
        if user.role == "admin":
            return Task.objects.all()

        elif user.role == "hod":
            # Show tasks created by HOD or assigned to HOD
            return Task.objects.filter(Q(user=user) | Q(assigned_to=user)).distinct()

        elif user.role == "supervisor":
            # Show tasks created by supervisor or assigned to supervisor
            return Task.objects.filter(Q(user=user) | Q(assigned_to=user)).distinct()

        else:
            # Normal user: show only tasks assigned to them or created by them
            return Task.objects.filter(Q(user=user) | Q(assigned_to=user)).distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # assign creator automatically


class TaskDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


# --------------------------
# EmailTemplate API Views
# --------------------------
class EmailTemplateListAPIView(generics.ListCreateAPIView):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class EmailTemplateDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


# --------------------------
# Employee List API
# --------------------------
class EmployeeListAPI(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
