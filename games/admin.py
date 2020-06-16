import json

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.auth.admin import UserAdmin
from django.urls import path, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.generic import CreateView, FormView

from .models import Card, Chug, Game, GamePlayer, User
from .serializers import GameSerializer
from .views import update_game


class AutocompleteModelChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hack to make AutocompleteSelect work for non-foreign key
        class FakeRemoteField:
            model = self.queryset.model

        self.widget = AutocompleteSelect(FakeRemoteField, admin.site)


class MergeUsersForm(forms.Form):
    user1 = AutocompleteModelChoiceField(label="User 1", queryset=User.objects.all())
    user2 = AutocompleteModelChoiceField(
        label="User 2", help_text="(will be deleted)", queryset=User.objects.all()
    )

    def clean(self):
        super().clean()
        if "user1" in self.cleaned_data and self.cleaned_data.get(
            "user1"
        ) == self.cleaned_data.get("user2"):
            raise forms.ValidationError("Please pick two different users.")

    def merge_users(self):
        self.cleaned_data["user1"].merge_with(self.cleaned_data["user2"])
        return self.cleaned_data["user1"]


@method_decorator(staff_member_required, name="dispatch")
class CustomAdminFormView(FormView):
    def __init__(self, *args, **kwargs):
        self.template_name = "admin/custom_form.html"
        self.success_url = reverse_lazy(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
        )
        self.model_admin = admin.site._registry[self.model]
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["opts"] = self.model._meta
        context["has_view_permission"] = self.model_admin.has_view_permission(
            self.request
        )
        context["title"] = self.title
        return context


class MergeUsersView(CustomAdminFormView):
    form_class = MergeUsersForm
    model = User
    title = "Merge users"

    def form_valid(self, form):
        user = form.merge_users()
        messages.success(
            self.request,
            format_html(
                "Users successfully merged to: <a href='{}'>{}</a>.",
                user.get_absolute_url(),
                user.username,
            ),
        )
        return super().form_valid(form)


@admin.register(User)
class UserAdminWithImage(UserAdmin):
    model = User

    fieldsets = UserAdmin.fieldsets + (("Image", {"fields": ("image",)}),)

    def get_urls(self):
        return [path("merge/", MergeUsersView.as_view())] + super().get_urls()


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
            game_id = None

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
