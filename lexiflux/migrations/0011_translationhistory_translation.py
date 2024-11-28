# Generated by Django 5.1 on 2024-10-01 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lexiflux', '0010_languagegroup_wordsexport_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='translationhistory',
            name='translation',
            field=models.TextField(default='', help_text='Translation of the term'),
            preserve_default=False,
        ),
    ]