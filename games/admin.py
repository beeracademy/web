from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Game, Card, Chug, GamePlayer


@admin.register(User)
class UserAdminWithImage(UserAdmin):
    model = User

    fieldsets = UserAdmin.fieldsets + (("Image", {"fields": ("image",)}),)


@admin.register(GamePlayer)
class GamePlayerAdmin(admin.ModelAdmin):
    readonly_fields = ["game", "user", "position"]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    readonly_fields = ["game", "index", "value", "suit"]


@admin.register(Chug)
class ChugAdmin(admin.ModelAdmin):
    readonly_fields = ["card"]


class GamePlayerInline(admin.TabularInline):
    model = GamePlayer
    readonly_fields = GamePlayerAdmin.readonly_fields


class CardInline(admin.TabularInline):
    model = Card
    readonly_fields = CardAdmin.readonly_fields


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    inlines = [GamePlayerInline, CardInline]
    list_filter = ["official"]
