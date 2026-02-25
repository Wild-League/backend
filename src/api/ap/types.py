from enum import Enum

class ActivityType(str, Enum):
	Follow = "Follow"
	Unfollow = "Unfollow"
	Accept = "Accept"
	Reject = "Reject"

class ActorType(str, Enum):
	Person = "Person"
	Group = "Group" # future clan implementation
	# Service = "Service"
	# Application = "Application"
