from django.conf import settings
from datetime import datetime
from rest_framework import serializers
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from .models import Deck, Card, Users, UsersRelationship, Waitlist
from .enums import ActorType, RelationshipType
import hashlib


class WaitlistSerializer(serializers.ModelSerializer):
	email = serializers.EmailField(write_only=True)

	class Meta:
		model = Waitlist
		fields = ['id', 'email']


class AuthSerializer(serializers.ModelSerializer):
	username = serializers.CharField()
	email = serializers.EmailField()
	password = serializers.CharField(write_only=True)
	# agreement = serializers.BooleanField(write_only=True)

	def validate(self, data):
		if Users.objects.filter(email=data['email']).exists():
			raise serializers.ValidationError("Email already exists")

		if Users.objects.filter(username=data['username']).exists():
			raise serializers.ValidationError("Username already exists")

		return data

	def save(self):
		username = self.validated_data['username']

		private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

		public_key = private_key.public_key().public_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PublicFormat.SubjectPublicKeyInfo
		)

		new_private_key = private_key.private_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PrivateFormat.TraditionalOpenSSL,
			encryption_algorithm=serialization.NoEncryption()
		)

		user = Users(
			email=self.validated_data['email'],
			username=username,
			# agreement=self.validated_data['agreement'],
			type=ActorType.PERSON.value,
			display_name=f'@{username}{settings.DOMAIN}',
			domain=settings.DOMAIN,
			level=1,
			url=f'{settings.FRONT_URL}{username}',
			long_url=f'{settings.FRONT_URL}{username}/json',
			inbox_url=f'{settings.FRONT_URL}{username}/inbox',
			outbox_url=f'{settings.FRONT_URL}{username}/outbox',
			created_at=datetime.now(),
			public_key=public_key.decode('utf-8'),
			private_key=new_private_key.decode('utf-8')
		)

		user.set_password(self.validated_data['password'])
		user.save()

		return user

	class Meta:
		model = Users
		fields = ['username', 'email', 'password', 'agreement']


class CardSerializer(serializers.ModelSerializer):
	class Meta:
		model = Card
		fields = ['id', 'name', 'type', 'cooldown', 'damage', 'attack_range', 'speed', 'life', 'img_card', 'img_preview', 'img_attack', 'img_death', 'img_walk', 'frame_width', 'frame_height']


class DeckSerializer(serializers.ModelSerializer):
	class Meta:
		model = Deck
		fields = ['id', 'name', 'created_at', 'updated_at']


class DeckCardsSerializer(serializers.ModelSerializer):
	cards =	CardSerializer(many=True)

	class Meta:
		model = Deck
		fields = ['id', 'name', 'cards']


class UsersSerializer(serializers.ModelSerializer):


	class Meta:
		model = Users
		fields = ['id', 'username', 'email', 'level']


class UsersRelationshipSerializer(serializers.ModelSerializer):
	user_id_related = serializers.PrimaryKeyRelatedField(queryset=Users.objects.all())
	relationship_type = serializers.ChoiceField(choices=RelationshipType.choices)
	activity_id = serializers.CharField()

	def save(self):
		self.validated_data['created_at'] = datetime.now()
		return super().save()

	def list_friends(self):
		friends_list = super().list()

		for friend in friends_list:
			user = Users.objects.get(id=friend['user_id_requester'])
			friend['requester_name'] = user.username

		return friends_list

	class Meta:
		model = UsersRelationship
		fields = ['id', 'user_id_requester', 'user_id_related', 'relationship_type', 'activity_id']
