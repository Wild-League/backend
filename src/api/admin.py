from django.contrib import admin
from .models import Users

@admin.register(Users)
class UserAdmin(admin.ModelAdmin):
	search_fields = ["username"]
	list_display = ["username", "created_at"]
