from rest_framework import permissions


class IsInternalStaff(permissions.BasePermission):
    """Permits access strictly to Lab Staff or Super Administrators."""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_internal() or request.user.role in [ request.user.Role.ADMIN])
        )


class IsCoachOwner(permissions.BasePermission):
    """Ensures Coaches only see their own profile, ledger, and assigned clients."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_coach())

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "coach_profile"):
            return obj.coach_profile.user == request.user
        if hasattr(obj, "assigned_clients") and obj.assigned_coach:
            return obj.assigned_coach.user == request.user
       
        return False


class IsClientOwner(permissions.BasePermission):
    """Ensures Clients only access their own direct records and diagnostic orders."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_client())

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "client_profile"):
            return obj.client_profile.user == request.user
        if hasattr(obj, "client") and obj.client:
            return obj.client.user == request.user
        return False


class DocumentAccessPermission(permissions.BasePermission):
    """
    Object-level check for document downloads:
    Allowed if Staff/Admin, or ordering Coach, or the owner Client.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_internal():
            return True
        if user.is_coach() and obj.assigned_coach:
            return obj.assigned_coach.user == user
        if user.is_client() and obj.client:
            return obj.client.user == user
        return False