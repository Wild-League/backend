import base64
import hashlib
import json
import time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from src.api.ap.types import ActivityType


class Reject():
	def __init__(self, actor, target_actor, friend_request_id, object_id):
		self.type = ActivityType.Reject
		self.actor = actor
		self.target_actor = target_actor
		self.friend_request_id = friend_request_id
		self.object_id = object_id

	def send(self):
		activity = self.to_dict()

		activity_digest = base64.b64encode(hashlib.sha256(json.dumps(activity).encode()).digest()).decode('utf-8')

		key_id = f'{self.actor.long_url}#main-key'

		current_time = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

		headers = f'''(request-target): post {self.target_actor.inbox_url}
		\nhost: {self.target_actor.inbox_url}
		\ndate: {current_time}
		\ndigest: sha-256={activity_digest}'''

		private_key = serialization.load_pem_private_key(bytes(self.actor.private_key, 'utf-8'), password=None)

		signature = base64.b64encode(private_key.sign(headers.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())).decode('utf-8')

		headers = {
			'Host': self.target_actor.inbox_url,
			'Date': current_time,
			'Digest': f'sha-256={activity_digest}',
			'Signature': f'keyId="{key_id}",algorithm="rsa-sha256",headers="(request-target) host date digest",signature="{signature}"',
			'Content-Type': 'application/activity+json'
		}

		requests.post(self.target_actor.inbox_url, headers=headers, json=activity)


	def to_dict(self):
		return {
			"@context": "https://www.w3.org/ns/activitystreams",
			"id": f"{self.actor.long_url}#rejects/follows/{self.friend_request_id}",
			"type": "Reject",
			"actor": self.actor.long_url,
			"object": {
				"id": self.object_id,
				"type": "Follow",
				"actor": self.actor.long_url,
				"object": self.target_actor.long_url
			}
		}

