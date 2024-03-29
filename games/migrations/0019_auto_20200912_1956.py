# Generated by Django 3.0.8 on 2020-09-12 17:56

from django.contrib.auth.hashers import make_password
from django.db import migrations


def fix_invalid_hashes(apps, schema_editor):
    User = apps.get_model("games", "User")
    for u in User.objects.filter(password="bcrypt$"):
        u.password = make_password("test")
        u.save()


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0018_game_image"),
    ]

    operations = [
        migrations.RunPython(fix_invalid_hashes),
    ]
