from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UserManager
from src.api.enums import RelationshipType


class Users(AbstractBaseUser):
	id = models.AutoField(primary_key=True)
	username = models.CharField(max_length=25, unique=True)
	display_name = models.CharField(max_length=85)
	bio = models.CharField(max_length=500, blank=True, null=True)
	domain = models.CharField(max_length=60)
	url = models.CharField(max_length=255)
	long_url = models.CharField(max_length=255, blank=True, null=True)
	type = models.TextField()
	inbox_url = models.CharField(max_length=255)
	outbox_url = models.CharField(max_length=255)
	icon = models.CharField(max_length=255)
	edited_at = models.DateField(blank=True, null=True)
	created_at = models.DateField(null=True)
	level = models.IntegerField()
	email = models.CharField(max_length=100)
	password = models.CharField(max_length=100)
	agreement = models.BooleanField(blank=True, null=True)
	public_key = models.CharField(blank=True, null=True)
	private_key = models.CharField(blank=True, null=True)

	is_superuser = models.BooleanField(blank=True, null=True)
	is_staff = models.BooleanField(blank=True, null=True)

	objects = UserManager()

	USERNAME_FIELD = "username"
	REQUIRED_FIELDS = []

	class Meta:
		db_table = 'users'


class Card(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=60)
	type = models.CharField(max_length=60)
	life = models.IntegerField(blank=True, null=True)
	speed = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	attack_range = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	cooldown = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	damage = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	frame_width = models.IntegerField(blank=True, null=True)
	frame_height = models.IntegerField(blank=True, null=True)
	created_at = models.DateField()
	updated_at = models.DateField(blank=True, null=True)

	img_card = models.CharField(max_length=255, blank=True, null=True)
	img_preview = models.CharField(max_length=255, blank=True, null=True)
	img_attack = models.CharField(max_length=255, blank=True, null=True)
	img_death = models.CharField(max_length=255, blank=True, null=True)
	img_walk = models.CharField(max_length=255, blank=True, null=True)

	class Meta:
		db_table = 'card'


class Deck(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=25)
	user_id = models.ForeignKey(Users, on_delete=models.RESTRICT, db_column="user_id")
	created_at = models.DateField()
	updated_at = models.DateField(blank=True, null=True)
	cards = models.ManyToManyField(Card, through="DeckCard")
	is_selected = models.BooleanField(default=False)

	class Meta:
		db_table = 'deck'


class DeckCard(models.Model):
	deck = models.ForeignKey(Deck, on_delete=models.PROTECT)
	card = models.ForeignKey(Card, on_delete=models.PROTECT)

	class Meta:
		db_table = 'deck_card'


class Posts(models.Model):
	id = models.AutoField(primary_key=True)
	created_at = models.DateField()
	edited_at = models.DateField(blank=True, null=True)
	user_id = models.ForeignKey(Users, on_delete=models.RESTRICT, db_column="user_id")
	content = models.CharField(max_length=255)
	in_reply_to_post_id = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, db_column="in_reply_to_post_id")

	class Meta:
		db_table = 'posts'


class Rules(models.Model):
	id = models.AutoField(primary_key=True)
	text = models.CharField(max_length=255)
	created_at = models.DateField()
	updated_at = models.DateField(blank=True, null=True)

	class Meta:
		db_table = 'rules'


class UsersRelationship(models.Model):
	user_id_requester = models.ForeignKey(Users, on_delete=models.RESTRICT, db_column="user_id_requester", related_name="user_id_requester")
	user_id_related = models.ForeignKey(Users, on_delete=models.RESTRICT, db_column="user_id_related", related_name="user_id_related")
	relationship_type = models.CharField(max_length=25, choices=RelationshipType.choices)
	created_at = models.DateField()
	updated_at = models.DateField(blank=True, null=True)
	activity_id = models.CharField(max_length=255, blank=True, null=True)

	class Meta:
		db_table = 'users_relationship'


class Waitlist(models.Model):
	id = models.AutoField(primary_key=True)
	email = models.CharField(max_length=100)

	class Meta:
		db_table = 'waitlist'
