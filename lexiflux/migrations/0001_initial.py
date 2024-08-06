# Generated by Django 5.0 on 2024-08-04 12:42

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

from lexiflux.language.google_languages import populate_languages


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('google_code', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('epub_code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.RunPython(populate_languages, None),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=100, unique=True)),
                ('public', models.BooleanField(default=False)),
                ('title', models.CharField(max_length=200)),
                ('toc', models.JSONField(blank=True, default=list)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lexiflux.author')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_books', to=settings.AUTH_USER_MODEL)),
                ('shared_with', models.ManyToManyField(blank=True, related_name='shared_books', to=settings.AUTH_USER_MODEL)),
                ('language', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='lexiflux.language')),
            ],
        ),
        migrations.CreateModel(
            name='BookFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_blob', models.BinaryField()),
                ('book', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='original_file', to='lexiflux.book')),
            ],
        ),
        migrations.CreateModel(
            name='LanguagePreferences',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inline_translation_type', models.CharField(choices=[('Translate', 'Translate'), ('Sentence', 'Sentence'), ('Explain', 'Explain'), ('Lexical', 'Lexical'), ('AI', 'AI'), ('Dictionary', 'Dictionary'), ('Site', 'Site')], default='Translate', max_length=20)),
                ('inline_translation_parameters', models.JSONField(default=dict)),
                ('current_book', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='current_readers', to='lexiflux.book')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='language_preferences', to='lexiflux.language')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='language_preferences', to=settings.AUTH_USER_MODEL)),
                ('user_language', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='language_preferences_user_language', to='lexiflux.language')),
            ],
            options={
                'unique_together': {('user', 'language')},
            },
        ),
        migrations.AddField(
            model_name='customuser',
            name='default_language_preferences',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='default_for_users', to='lexiflux.languagepreferences'),
        ),
        migrations.CreateModel(
            name='ReadingHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_number', models.PositiveIntegerField()),
                ('top_word_id', models.PositiveIntegerField()),
                ('read_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lexiflux.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reading_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-read_time'],
            },
        ),
        migrations.CreateModel(
            name='AIModelConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_model', models.CharField(help_text='LangChain Chat model class', max_length=100)),
                ('settings', models.JSONField(blank=True, default=dict, help_text='AI model settings.')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_model_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'chat_model')},
            },
        ),
        migrations.CreateModel(
            name='BookPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField()),
                ('content', models.TextField()),
                ('word_slices', models.JSONField(blank=True, help_text='List of tuples with start and end index for each word.', null=True)),
                ('word_to_sentence_map', models.JSONField(blank=True, null=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='lexiflux.book')),
            ],
            options={
                'ordering': ['number'],
                'unique_together': {('book', 'number')},
            },
        ),
        migrations.CreateModel(
            name='LexicalArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('Translate', 'Translate'), ('Sentence', 'Sentence'), ('Explain', 'Explain'), ('Lexical', 'Lexical'), ('AI', 'AI'), ('Dictionary', 'Dictionary'), ('Site', 'Site')], max_length=20)),
                ('title', models.CharField(max_length=100)),
                ('parameters', models.JSONField(default=dict)),
                ('language_preferences', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lexical_articles', to='lexiflux.languagepreferences')),
            ],
            options={
                'unique_together': {('language_preferences', 'title')},
            },
        ),
        migrations.CreateModel(
            name='ReadingLoc',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_number', models.PositiveIntegerField(help_text='Page number currently being read')),
                ('word', models.PositiveIntegerField(help_text='Last word read on the current reading page')),
                ('updated', models.DateTimeField(default=django.utils.timezone.now)),
                ('furthest_reading_page', models.PositiveIntegerField(default=0, help_text='Stores the furthest reading page number')),
                ('furthest_reading_word', models.PositiveIntegerField(default=0, help_text='Stores the furthest reading top word on the furthest page')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lexiflux.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reading_pos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'book')},
            },
        ),
    ]
