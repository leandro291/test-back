from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import RoleFilter
from .models import Role
from .permissions import IsAdminOrReadOnly
from .serializers import RoleSerializer, RoleUpdateSerializer


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD for business roles: read for authenticated users, write for staff."""

    queryset = Role.objects.with_user_count()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_class = RoleFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return RoleUpdateSerializer
        return RoleSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'No se puede eliminar un rol con usuarios asignados.'},
                status=status.HTTP_409_CONFLICT,
            )
