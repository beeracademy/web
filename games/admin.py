from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Game, Card, Chug


@admin.register(User)
class UserAdminWithImage(UserAdmin):
	model = User

	fieldsets = UserAdmin.fieldsets + (
		('Image', {'fields': ('image',)}),
	)

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
	pass

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
	pass

@admin.register(Chug)
class ChugAdmin(admin.ModelAdmin):
	pass
