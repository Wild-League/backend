from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from ..serializers import DeckSerializer, DeckCardsSerializer
from ..models import Deck

class DeckModelViewSet(viewsets.ModelViewSet):
	queryset = Deck.objects.all()
	serializer_class = DeckSerializer
	permission_classes = [IsAuthenticatedOrReadOnly]

	def list(self, request):
		print(request)
		user_id = request.user.id
		decks = Deck.objects.filter(user_id=user_id)
		serialized_decks = DeckSerializer(decks, many=True).data
		return Response(data=serialized_decks, status=status.HTTP_200_OK)

	def retrieve(self, request, pk):
		try:
			deck = Deck.objects.get(pk=pk)
		except Deck.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

		serialized_deck = DeckCardsSerializer(deck).data
		return Response(data=serialized_deck, status=status.HTTP_200_OK)

	@action(detail=False, methods=['get'])
	def current(self, request):
		print(request.user.id)

		user_id = request.user.id
		deck = Deck.objects.filter(user_id=user_id, is_selected=True).first()

		print(deck)

		if not deck:
			return Response(status=status.HTTP_404_NOT_FOUND)

		serialized_deck = DeckCardsSerializer(deck).data
		return Response(data=serialized_deck, status=status.HTTP_200_OK)

