from rest_framework.response import Response
from rest_framework import viewsets, status
from ..serializers import AuthSerializer

class AuthModelViewSet(viewsets.ModelViewSet):
	permission_classes = []

	def signup(self, request):
		serializer = AuthSerializer(data=request.data)

		if serializer.is_valid():
			serializer.save()
			return Response(status=status.HTTP_201_CREATED)

		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
