# Generated by Django 2.2.3 on 2019-08-05 22:37

import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
import games.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("auth", "0011_update_proxy_permissions")]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                ("email", models.EmailField(blank=True, max_length=254)),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=games.models.get_user_image_name,
                    ),
                ),
                ("old_password_hash", models.CharField(blank=True, max_length=60)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={"ordering": ("username",)},
            managers=[("objects", games.models.CaseInsensitiveUserManager())],
        ),
        migrations.CreateModel(
            name="Card",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("index", models.PositiveSmallIntegerField()),
                (
                    "value",
                    models.SmallIntegerField(
                        choices=[
                            (2, "2"),
                            (3, "3"),
                            (4, "4"),
                            (5, "5"),
                            (6, "6"),
                            (7, "7"),
                            (8, "8"),
                            (9, "9"),
                            (10, "10"),
                            (11, "Jack"),
                            (12, "Queen"),
                            (13, "King"),
                            (14, "Ace"),
                        ]
                    ),
                ),
                (
                    "suit",
                    models.CharField(
                        choices=[
                            ("S", "Spades"),
                            ("C", "Clubs"),
                            ("H", "Hearts"),
                            ("D", "Diamonds"),
                            ("A", "Carls"),
                            ("I", "Heineken"),
                        ],
                        max_length=1,
                    ),
                ),
                ("drawn_datetime", models.DateTimeField()),
            ],
            options={"ordering": ("index",)},
        ),
        migrations.CreateModel(
            name="Chug",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("duration_in_milliseconds", models.PositiveIntegerField()),
                (
                    "card",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chug",
                        to="games.Card",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "start_datetime",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("end_datetime", models.DateTimeField(blank=True, null=True)),
                ("sips_per_beer", models.PositiveSmallIntegerField(default=14)),
                ("description", models.CharField(blank=True, max_length=1000)),
                ("official", models.BooleanField(default=True)),
            ],
            options={"ordering": ("-end_datetime",)},
        ),
        migrations.CreateModel(
            name="PlayerStat",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("season_number", models.PositiveIntegerField()),
                ("total_games", models.PositiveIntegerField()),
                ("total_time_played_seconds", models.FloatField()),
                ("total_sips", models.PositiveIntegerField()),
                ("best_game_sips", models.PositiveIntegerField(null=True)),
                ("worst_game_sips", models.PositiveIntegerField(null=True)),
                ("total_chugs", models.PositiveIntegerField()),
                ("average_chug_time_seconds", models.FloatField(null=True)),
                (
                    "best_game",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="games.Game",
                    ),
                ),
                (
                    "fastest_chug",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="games.Chug",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "worst_game",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="games.Game",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GamePlayer",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("position", models.PositiveSmallIntegerField()),
                ("dnf", models.BooleanField(default=False)),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="games.Game"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("position",),
                "unique_together": {("game", "user", "position")},
            },
        ),
        migrations.AddField(
            model_name="game",
            name="players",
            field=models.ManyToManyField(
                through="games.GamePlayer", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cards",
                to="games.Game",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="card", unique_together={("game", "index"), ("game", "value", "suit")}
        ),
    ]
