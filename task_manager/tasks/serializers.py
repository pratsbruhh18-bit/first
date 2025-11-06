# tasks/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import Task, EmailTemplate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()

# -------------------------------
# User serializers
# -------------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class TaskSerializer(serializers.ModelSerializer):
    # Nested read-only fields
    assigned_to = UserSerializer(many=True, read_only=True)
    completed_by = UserSerializer(read_only=True)
    user = UserSerializer(read_only=True)  # creator

    # Writeable field for assigning multiple users by ID
    assigned_to_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        write_only=True,
        required=False
    )

    # Permission field
    can_delete = serializers.SerializerMethodField()
    
    # Completed user ID(s) field
    completed_user_ids = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'description',
            'user',
            'assigned_to',       # nested read-only list
            'assigned_to_ids',   # write-only list of IDs
            'completed',
            'completed_by',
            'due_date',
            'created_at',
            'updated_at',
            'can_delete',        # permission flag
            'completed_user_ids' # list of IDs who completed task
        ]

    def get_can_delete(self, obj):
        """Check if the requesting user can delete this task."""
        user = self.context['request'].user
        if user.role == "hod":
            return False
        if user.role == "supervisor" and obj.user.role not in ["operator", "supervisor"]:
            return False
        if user.role in ["operator", "user"] and obj.user != user:
            return False
        return True

    def get_completed_user_ids(self, obj):
        """Return list of IDs of users who completed the task (currently only one)."""
        return [obj.completed_by.id] if obj.completed_by else []

    def create(self, validated_data):
        assigned_users = validated_data.pop("assigned_to_ids", [])
        task = Task.objects.create(**validated_data)
        task.assigned_to.set(assigned_users)
        return task

    def update(self, instance, validated_data):
        assigned_users = validated_data.pop("assigned_to_ids", serializers.empty)

        # Update normal fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Set completed_by if task marked completed
        if "completed" in validated_data and validated_data["completed"]:
            instance.completed_by = self.context['request'].user

        instance.save()

        # Update assigned users if explicitly provided
        if assigned_users is not serializers.empty:
            instance.assigned_to.set(assigned_users)

        return instance


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
# Auth / User registration serializers
# -------------------------------
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

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
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['role'] = self.user.role
        return data
