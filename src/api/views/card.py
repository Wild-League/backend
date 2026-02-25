from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Q
from ..serializers import CardSerializer
from ..models import Card

class CardModelViewSet(viewsets.ModelViewSet):
	queryset = Card.objects.all()
	serializer_class = CardSerializer
	permission_classes = [IsAuthenticatedOrReadOnly]

	def list(self, request):
		limit = self.request.query_params.get('limit', None)
		name = self.request.query_params.get('name', None)

		if limit:
			limit = int(limit)

		name_filter = Q()

		if name:
			name_filter = Q(name__icontains=name)

		queryset = Card.objects.all().filter(name_filter).order_by('id')[:limit]
		serializer = CardSerializer(queryset, many=True)

		return Response(serializer.data)
