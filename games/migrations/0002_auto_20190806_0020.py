# Generated by Django 2.2.3 on 2019-08-06 00:20

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("games", "0001_initial")]

    operations = [
        migrations.AlterUniqueTogether(
            name="playerstat", unique_together={("user", "season_number")}
        )
    ]
