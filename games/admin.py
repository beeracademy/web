import json

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.views.generic import CreateView

from .models import Card, Chug, Game, GamePlayer, User
from .serializers import GameSerializer
from .views import update_game


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


class UploadGameView(CreateView):
    model = Game
    fields = []
    template_name = "admin/games/game/upload_game.html"


class UploadForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ["game_log", "fix_times"]

    game_log = forms.CharField(widget=forms.Textarea(attrs={"rows": 30, "cols": 55}))
    fix_times = forms.BooleanField(required=False)

    def clean(self):
        log = self.cleaned_data["game_log"]
        try:
            data = json.loads(log)
        except:
            raise forms.ValidationError("Invalid JSON")

        try:
            game_id = int(data["id"])
        except (KeyError, ValueError):
            raise forms.ValidationError("Invalid game id")

        game, created = Game.objects.get_or_create(
            id=game_id, defaults={"start_datetime": None}
        )

        s = GameSerializer(
            game,
            data=data,
            context={
                "fix_times": self.cleaned_data["fix_times"],
                "ignore_finished": True,
            },
        )
        if not s.is_valid():
            raise forms.ValidationError(str(s.errors))

        self.cleaned_data["game"] = game
        self.cleaned_data["validated_data"] = s.validated_data

    def save(self, commit=True):
        game = self.cleaned_data["game"]
        game.dnf = False
        game.save()
        update_game(game, self.cleaned_data["validated_data"])
        return game

    def save_m2m(self):
        pass


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_filter = ["official"]
    add_form_template = "admin/games/game/upload_game.html"
    save_on_top = True

    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            self.inlines = []
            return UploadForm
        else:
            self.inlines = [GamePlayerInline, CardInline]
            return super().get_form(request, obj, **kwargs)
