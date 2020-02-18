# Generated by Django 2.2.8 on 2020-02-18 16:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0008_game_dnf"),
    ]

    operations = [
        migrations.CreateModel(
            name="GamePlayerStat",
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
                ("value_sum", models.PositiveIntegerField()),
                ("aces", models.PositiveIntegerField()),
                (
                    "gameplayer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="games.GamePlayer",
                    ),
                ),
            ],
        ),
    ]
