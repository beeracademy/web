# Generated by Django 3.0.7 on 2020-07-20 17:17

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="failedgameupload",
            name="created",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="failedgameupload",
            name="game_log",
            field=models.TextField(),
        ),
    ]
