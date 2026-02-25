from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

# from src.api.enums import RelationshipType
from ..serializers import UsersSerializer
from ..models import Users

class UsersModelViewSet(viewsets.ModelViewSet):
	queryset = Users.objects.all()
	serializer_class = UsersSerializer
	permission_classes = [IsAuthenticatedOrReadOnly]

	def retrieve(self, request, pk=None):
		try:
			user = Users.objects.get(username=pk)

			response_data = {
				"@context": "https://www.w3.org/ns/activitystreams",
				"id": f"{user.url}/json",
				"type": "Person",
				"preferredUsername": user.username,
				"inbox": user.inbox_url,
				"outbox": user.outbox_url,
				"url": user.url,
				"publicKey": {
					"id": f"{user.url}/json#main-key",
					"owner": user.url,
					"publicKeyPem": user.public_key
				}
			}

			return Response(response_data)
		except Users.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

	@action(detail=False, methods=['get'])
	def me(self, request):
		user_id = request.user.id
		user = Users.objects.get(id=user_id)
		serialized_user = UsersSerializer(user).data
		return Response(data=serialized_user, status=status.HTTP_200_OK)
