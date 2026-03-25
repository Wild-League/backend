from django.test import TestCase
from rest_framework.test import APIClient


class NodeInfoViewTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_well_known_nodeinfo(self):
		response = self.client.get('/.well-known/nodeinfo')
		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertEqual(len(body['links']), 1)
		self.assertEqual(
			body['links'][0]['rel'],
			'http://nodeinfo.diaspora.software/ns/schema/2.1',
		)
		self.assertIn('/nodeinfo/2.1', body['links'][0]['href'])

	def test_nodeinfo_2_1(self):
		response = self.client.get('/nodeinfo/2.1')
		self.assertEqual(response.status_code, 200)
		self.assertIn('application/json', response['Content-Type'])
		self.assertIn(
			'http://nodeinfo.diaspora.software/ns/schema/2.1#',
			response['Content-Type'],
		)
		body = response.json()
		self.assertEqual(body['version'], '2.1')
		self.assertEqual(body['software']['name'], 'wildleague')
		self.assertEqual(body['protocols'], ['activitypub'])
		self.assertIn('total', body['usage']['users'])
		self.assertEqual(body['metadata']['name'], 'WildLeague')
