# Generated by Django 5.1.2 on 2024-10-27 09:19

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lexiflux', '0015_alter_translationhistory_first_lookup_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReaderSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('font_family', models.CharField(help_text='Font family name or system font stack', max_length=255)),
                ('font_size', models.CharField(help_text="Font size with units (e.g., '16px')", max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('book', models.ForeignKey(blank=True, help_text="If null, these are the user's default font settings", null=True, on_delete=django.db.models.deletion.CASCADE, to='lexiflux.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reader_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
                'indexes': [models.Index(fields=['user', 'book'], name='lexiflux_re_user_id_7e5912_idx'), models.Index(fields=['user', '-updated_at'], name='lexiflux_re_user_id_1da290_idx')],
                'unique_together': {('user', 'book')},
            },
        ),
    ]