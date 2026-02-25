from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.conf import settings
import uuid

from src.api.ap.activities.follow import Follow
from src.api.ap.activities.accept import Accept
from src.api.ap.activities.reject import Reject

from src.api.enums import RelationshipType
from ..serializers import UsersRelationshipSerializer
from ..models import UsersRelationship, Users

class UsersRelationshipModelViewSet(viewsets.ModelViewSet):
	queryset = UsersRelationship.objects.all()
	serializer_class = UsersRelationshipSerializer
	permission_classes = [IsAuthenticatedOrReadOnly]

	def create(self, request):
		data = request.data
		data['user_id_requester'] = request.user.id
		data['relationship_type'] = RelationshipType.FriendRequest

		if data.get('username'):
			try:
				sender_user = Users.objects.get(username=request.user)
				target_user = Users.objects.get(username=data['username'])
				data['user_id_related'] = target_user.id

				id = uuid.uuid4()
				data['activity_id'] = f'{settings.FRONT_URL}{id}'

				follow = Follow(sender_user, target_user, data['activity_id'])
				follow.send()
			except Users.DoesNotExist:
				return Response({ 'error': 'User not found' }, status=status.HTTP_404_NOT_FOUND)
		else:
			return Response({ 'error': 'Username is required' }, status=status.HTTP_400_BAD_REQUEST)


		existing_relationship = UsersRelationship.objects.filter(
			user_id_requester=data['user_id_requester'],
			user_id_related=data['user_id_related']
		).first()

		if existing_relationship:
			return Response(status=status.HTTP_200_OK)

		serialized_relationship = UsersRelationshipSerializer(data=data)

		if serialized_relationship.is_valid():
			serialized_relationship.save()
			return Response(status=status.HTTP_201_CREATED)

		return Response(data=serialized_relationship.errors, status=status.HTTP_400_BAD_REQUEST)


	# TODO: split into `list_of_friend_requests` and `list_of_friends`
	def list(self, request):
		user_id = request.user.id
		relationships = UsersRelationship.objects.filter(user_id_related=user_id)
		serialized_relationships = UsersRelationshipSerializer(relationships, many=True).data

		for relationship in serialized_relationships:
			requester = Users.objects.get(id=relationship['user_id_requester'])
			relationship['requester_username'] = requester.username

		return Response(data=serialized_relationships, status=status.HTTP_200_OK)


	@action(detail=False, methods=['post'])
	def accept_friend_request(self, request):
		friend_request_id = request.data.get('friend_request_id')

		friend_request = UsersRelationship.objects.get(id=friend_request_id)

		friend_request.relationship_type = RelationshipType.Friend
		friend_request.save()

		accept = Accept(friend_request.user_id_requester, friend_request.user_id_related, friend_request.id, friend_request.activity_id)
		accept.send()

		return Response(status=status.HTTP_200_OK)


	@action(detail=False, methods=['post'])
	def reject_friend_request(self, request):
		friend_request_id = request.data.get('friend_request_id')
		friend_request = UsersRelationship.objects.get(id=friend_request_id)

		friend_request.relationship_type = RelationshipType.Rejected
		friend_request.save()

		reject = Reject(friend_request.user_id_requester, friend_request.user_id_related, friend_request.id, friend_request.activity_id)
		reject.send()

		return Response(status=status.HTTP_200_OK)
