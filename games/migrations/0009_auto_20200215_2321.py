# Generated by Django 2.2.8 on 2020-02-15 22:21

from django.db import migrations, models


def drawn_datetime_to_start_delta_ms(apps, schema_editor):
    Card = apps.get_model("games", "Card")
    for card in Card.objects.all():
        if card.drawn_datetime:
            td = card.drawn_datetime - card.game.start_datetime
            card.start_delta_ms = td.seconds * 1000 + td.microseconds // 1000
            card.save()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0008_game_dnf"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="start_delta_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(drawn_datetime_to_start_delta_ms),
        migrations.RemoveField(
            model_name="card",
            name="drawn_datetime",
        ),
        migrations.AddField(
            model_name="chug",
            name="start_start_delta_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="chug",
            name="duration_in_milliseconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
