# Generated by Django 5.1 on 2024-08-27 04:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lexiflux', '0006_book_anchor_map'),
    ]

    operations = [
        migrations.AlterField(
            model_name='readingloc',
            name='furthest_reading_word',
            field=models.IntegerField(default=0, help_text='Stores the furthest reading top word on the furthest page. -1 for no words on the page.'),
        ),
        migrations.AlterField(
            model_name='readingloc',
            name='word',
            field=models.IntegerField(help_text='Last word read on the current reading page. -1 for no words on the page.'),
        ),
    ]
