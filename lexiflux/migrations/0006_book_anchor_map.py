# Generated by Django 5.1 on 2024-08-22 03:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lexiflux', '0005_readingloc_last_position_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='anchor_map',
            field=models.JSONField(blank=True, default=dict, help_text='Maps anchors to page numbers and EPUB items'),
        ),
    ]
