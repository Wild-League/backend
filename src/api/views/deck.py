from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from ..serializers import (
	DeckSerializer,
	DeckCardsSerializer,
	DeckSetCardsSerializer,
	DeckSelectSerializer,
)
from ..models import Deck, Card

MAX_DECKS_PER_USER = 10

class DeckModelViewSet(viewsets.ModelViewSet):
	queryset = Deck.objects.all()
	serializer_class = DeckSerializer
	permission_classes = [IsAuthenticatedOrReadOnly]

	def list(self, request):
		user_id = request.user.id
		decks = Deck.objects.filter(user_id=user_id)
		serialized_decks = DeckSerializer(decks, many=True).data
		return Response(data=serialized_decks, status=status.HTTP_200_OK)

	def create(self, request) -> Response:
		if not request.user.is_authenticated:
			return Response(status=status.HTTP_401_UNAUTHORIZED)
		if Deck.objects.filter(user_id=request.user).count() >= MAX_DECKS_PER_USER:
			return Response(
				{'detail': 'Maximum %d decks per user.' % MAX_DECKS_PER_USER},
				status=status.HTTP_400_BAD_REQUEST,
			)
		serializer = DeckSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save(
				user_id=request.user,
				created_at=timezone.now().date(),
			)
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def retrieve(self, request, pk):
		try:
			deck = Deck.objects.get(pk=pk)
		except Deck.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

		if request.user.is_authenticated and deck.user_id.pk != request.user.pk:
			return Response(status=status.HTTP_403_FORBIDDEN)

		serialized_deck = DeckCardsSerializer(deck).data
		return Response(data=serialized_deck, status=status.HTTP_200_OK)

	def update(self, request, pk=None, partial: bool = False) -> Response:
		try:
			deck = Deck.objects.get(pk=pk)
		except Deck.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

		if deck.user_id.pk != request.user.pk:
			return Response(status=status.HTTP_403_FORBIDDEN)

		serializer = DeckSerializer(deck, data=request.data, partial=partial)
		if serializer.is_valid():
			serializer.save(updated_at=timezone.now().date())
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def partial_update(self, request, pk=None) -> Response:
		return self.update(request, pk, partial=True)

	def destroy(self, request, pk=None) -> Response:
		try:
			deck = Deck.objects.get(pk=pk)
		except Deck.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

		if deck.user_id.pk != request.user.pk:
			return Response(status=status.HTTP_403_FORBIDDEN)

		deck.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)

	@action(detail=False, methods=['get'])
	def current(self, request):
		user_id = request.user.id
		deck = Deck.objects.filter(user_id=user_id, is_selected=True).first()

		if not deck:
			return Response(status=status.HTTP_404_NOT_FOUND)

		serialized_deck = DeckCardsSerializer(deck).data
		return Response(data=serialized_deck, status=status.HTTP_200_OK)

	@action(detail=False, methods=['post'], url_path='select')
	def select(self, request):
		if not request.user.is_authenticated:
			return Response(status=status.HTTP_401_UNAUTHORIZED)
		serializer = DeckSelectSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		deck_id = serializer.validated_data['id']
		try:
			deck = Deck.objects.get(pk=deck_id, user_id=request.user)
		except Deck.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)
		with transaction.atomic():
			Deck.objects.filter(user_id=request.user).update(is_selected=False)
			deck.is_selected = True
			deck.save(update_fields=['is_selected'])
		return Response(DeckCardsSerializer(deck).data, status=status.HTTP_200_OK)

	@action(detail=True, methods=['post'], url_path='set_cards')
	def set_cards(self, request, pk=None):
		if not request.user.is_authenticated:
			return Response(status=status.HTTP_401_UNAUTHORIZED)
		try:
			deck = Deck.objects.get(pk=pk)
		except Deck.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)
		if deck.user_id.pk != request.user.pk:
			return Response(status=status.HTTP_403_FORBIDDEN)
		serializer = DeckSetCardsSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		card_ids = serializer.validated_data['card_ids']
		if card_ids:
			found = set(Card.objects.filter(id__in=card_ids).values_list('id', flat=True))
			missing = [cid for cid in card_ids if cid not in found]
			if missing:
				return Response(
					{'detail': 'Unknown card id(s): %s' % missing},
					status=status.HTTP_400_BAD_REQUEST,
				)
		with transaction.atomic():
			deck.cards.set(card_ids)
			deck.updated_at = timezone.now().date()
			deck.save(update_fields=['updated_at'])
		return Response(DeckCardsSerializer(deck).data, status=status.HTTP_200_OK)

