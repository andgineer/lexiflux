# Generated by Django 5.0 on 2024-07-02 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lexiflux", "0002_lexicalarticle"),
    ]

    operations = [
        migrations.AddField(
            model_name="readerprofile",
            name="inline_translation",
            field=models.TextField(blank=True),
        ),
    ]
