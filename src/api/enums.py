from enum import Enum
from django.db import models

class ActorType(str, Enum):
	PERSON = 'Person',
	GROUP = 'Group'


class RelationshipType(models.TextChoices):
	Block = 'Block'
	Friend = 'Friend'
	FriendRequest = 'FriendRequest',
	Rejected = 'Rejected' # Friend Request Rejected
