# Generated by Django 3.0.4 on 2020-04-22 18:37

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0012_merge_20200421_2322"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chug",
            old_name="duration_in_milliseconds",
            new_name="duration_ms",
        ),
    ]
