from datetime import timedelta

from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Users

NODEINFO_REL_2_1 = 'http://nodeinfo.diaspora.software/ns/schema/2.1'
# Protocol: retrieval should use profile matching the schema resolution scope.
NODEINFO_2_1_CONTENT_TYPE = (
	'application/json; profile="http://nodeinfo.diaspora.software/ns/schema/2.1#"'
)

SOFTWARE_HOMEPAGE = 'https://wildleague.org'
SOFTWARE_REPOSITORY = 'https://github.com/wild-league/game'
SOFTWARE_VERSION = '0.0.1'


class NodeInfoWellKnownView(APIView):
	"""Serves the NodeInfo discovery document at `/.well-known/nodeinfo`."""

	authentication_classes = []
	permission_classes = [AllowAny]

	def get(self, request):
		href = request.build_absolute_uri(reverse('nodeinfo-2-1'))
		return Response({
			'links': [
				{
					'rel': NODEINFO_REL_2_1,
					'href': href,
				},
			],
		})


class NodeInfo21View(APIView):
	"""Serves the NodeInfo 2.1 document."""

	authentication_classes = []
	permission_classes = [AllowAny]

	def get(self, request):
		now = timezone.now()
		month_ago = now - timedelta(days=30)
		half_year_ago = now - timedelta(days=180)

		total = Users.objects.count()
		active_month = Users.objects.filter(last_login__gte=month_ago).count()
		active_halfyear = Users.objects.filter(last_login__gte=half_year_ago).count()

		payload = {
			'version': '2.1',
			'software': {
				'homepage': SOFTWARE_HOMEPAGE,
				'name': 'wildleague',
				'version': SOFTWARE_VERSION,
				'repository': SOFTWARE_REPOSITORY,
			},
			'protocols': ['activitypub'],
			'services': {
				'outbound': [],
				'inbound': [],
			},
			'usage': {
				'users': {
					'total': total,
					'activeMonth': active_month,
					'activeHalfyear': active_halfyear,
				},
				'localPosts': 0,
				'localComments': 0,
			},
			'openRegistrations': True,
			'metadata': {
				'name': 'WildLeague',
				'nodeDescription': 'Gaming on fediverse',
			},
		}
		return JsonResponse(payload, content_type=NODEINFO_2_1_CONTENT_TYPE)
