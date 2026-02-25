from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from ..serializers import WaitlistSerializer
from ..models import Waitlist

class WaitlistModelViewSet(viewsets.ModelViewSet):
  queryset = Waitlist.objects.all()
  serializer_class = WaitlistSerializer
  permission_classes = []

  def create(self, request):
    serialized_waitlist = WaitlistSerializer(data=request.data)

    if serialized_waitlist.is_valid():
      serialized_waitlist.save()
      return Response(status=status.HTTP_201_CREATED)

    return Response(data=serialized_waitlist.errors, status=status.HTTP_400_BAD_REQUEST)
