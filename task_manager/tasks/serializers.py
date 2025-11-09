# tasks/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import Task, EmailTemplate, Department
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model


User = get_user_model()

# -------------------------------
# Department Serializer
# -------------------------------
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']

# -------------------------------
# User Serializer
# -------------------------------
class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "department"]

# -------------------------------
# Task Serializer
# -------------------------------
class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    completed_by = UserSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)

    # Writeable fields
    assigned_to_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), write_only=True, required=False
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), write_only=True, required=False
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), write_only=True, required=False, allow_null=True
    )

    # Metadata / permissions
    can_delete = serializers.SerializerMethodField()
    completed_user_ids = serializers.SerializerMethodField()
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'description',
            'user',
            'assigned_to',
            'assigned_to_ids',
            'completed',
            'completed_by',
            'due_date',
            'status',
            'department',
            'department_id',
            'parent_id',
            'subtasks',
            'task_number',
            'created_at',
            'updated_at',
            'can_delete',
            'completed_user_ids',
        ]

    # -------------------------------
    # Permissions & metadata
    # -------------------------------
    def get_can_delete(self, obj):
        user = self.context['request'].user
        if user.role == "hod":
            return False
        if user.role == "supervisor" and obj.user.role not in ["operator", "supervisor"]:
            return False
        if user.role in ["operator", "user"] and obj.user != user:
            return False
        return True

    def get_completed_user_ids(self, obj):
        return [obj.completed_by.id] if obj.completed_by else []

    def get_subtasks(self, obj):
        # Nested subtasks with minimal info
        subtasks = obj.subtasks.all().order_by("task_number")
        return [
            {
                "id": t.id,
                "title": t.title,
                "task_number": t.task_number,
                "completed": t.completed,
                "assigned_to": UserSerializer(t.assigned_to.all(), many=True).data,
            } for t in subtasks
        ]

    # -------------------------------
    # Create / Update Methods
    # -------------------------------
    def create(self, validated_data):
        assigned_users = validated_data.pop("assigned_to_ids", [])
        department = validated_data.pop("department_id", None)
        parent = validated_data.pop("parent_id", None)

        task = Task.objects.create(**validated_data)
        if department:
            task.department = department
        if parent:
            task.parent = parent
        task.save()

        if assigned_users:
            task.assigned_to.set(assigned_users)

        return task

    def update(self, instance, validated_data):
        assigned_users = validated_data.pop("assigned_to_ids", serializers.empty)
        department = validated_data.pop("department_id", serializers.empty)
        parent = validated_data.pop("parent_id", serializers.empty)

        # Update normal fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Mark completed by current user if completed
        if "completed" in validated_data and validated_data["completed"]:
            instance.completed_by = self.context['request'].user

        # Update department if provided
        if department is not serializers.empty:
            instance.department = department

        # Update parent/subtask if provided
        if parent is not serializers.empty:
            instance.parent = parent

        instance.save()

        # Update assigned users
        if assigned_users is not serializers.empty:
            instance.assigned_to.set(assigned_users)

        return instance


# -------------------------------
# EmailTemplate Serializer
# -------------------------------
class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            'id',
            'name',
            'subject',
            'body',
            'is_active',
            'created_at',
            'updated_at'
        ]


# -------------------------------
# Auth / User registration
# -------------------------------
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            role=validated_data.get('role', 'user')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        user = authenticate(username=attrs.get('username'), password=attrs.get('password'))
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        attrs['user'] = user
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        token['username'] = user.username
        if user.department:
            token['department'] = user.department.name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['role'] = self.user.role
        data['department'] = self.user.department.name if self.user.department else None
        return data
