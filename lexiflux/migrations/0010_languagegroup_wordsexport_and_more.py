# Generated by Django 5.1 on 2024-09-28 06:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from lexiflux.language.google_languages import populate_language_groups


class Migration(migrations.Migration):

    dependencies = [
        ('lexiflux', '0009_translationhistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanguageGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='WordsExport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('export_datetime', models.DateTimeField(auto_now_add=True)),
                ('word_count', models.PositiveIntegerField()),
                ('details', models.JSONField(default=dict, help_text='Details of the export, e.g., number of words, format')),
            ],
        ),
        migrations.AlterField(
            model_name='translationhistory',
            name='context',
            field=models.TextField(help_text='Context of the term. Sentence with the term surrounded with ‹§›. Place of the term inside marked with single ‹§›.'),
        ),
        migrations.AddIndex(
            model_name='translationhistory',
            index=models.Index(fields=['user', 'source_language'], name='lexiflux_tr_user_id_df9053_idx'),
        ),
        migrations.AddIndex(
            model_name='translationhistory',
            index=models.Index(fields=['user', 'source_language', 'last_lookup'], name='lexiflux_tr_user_id_0295b6_idx'),
        ),
        migrations.AddField(
            model_name='languagegroup',
            name='languages',
            field=models.ManyToManyField(related_name='language_groups', to='lexiflux.language'),
        ),
        migrations.AddField(
            model_name='wordsexport',
            name='language',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lexiflux.language'),
        ),
        migrations.AddField(
            model_name='wordsexport',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='words_exports', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='wordsexport',
            index=models.Index(fields=['user', 'language'], name='lexiflux_wo_user_id_939592_idx'),
        ),
        migrations.AddIndex(
            model_name='wordsexport',
            index=models.Index(fields=['user', 'language', '-export_datetime'], name='lexiflux_wo_user_id_a758f5_idx'),
        ),
        migrations.RunPython(populate_language_groups, migrations.RunPython.noop),
    ]