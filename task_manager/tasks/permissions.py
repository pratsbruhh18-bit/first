from rest_framework import permissions

class IsAdminHODSupervisorOrAssigned(permissions.BasePermission):
    """
    Admin: can do everything
    HOD: can edit tasks they created or assigned to them
    Supervisor: can edit tasks they created or assigned to them
    User: can only edit tasks assigned to them
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        print(user)

        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "admin":
            return True

        if getattr(user, "role", "") == "hod":
            print("hey")
            return True

        if getattr(user, "role", "") == "supervisor":
            return obj.user == user or user in obj.assigned_to.all()

        if getattr(user, "role", "") == "user":
            return user in obj.assigned_to.all()

        return False
