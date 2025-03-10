# Generated by Django 5.1.3 on 2024-11-30 10:56

from django.db import migrations, models
from lexiflux.models import normalize_for_search


def populate_normalized_content(apps, schema_editor):
    """Populate normalized_content for existing pages."""
    BookPage = apps.get_model('lexiflux', 'BookPage')
    for page in BookPage.objects.all():
        page.normalized_content = normalize_for_search(page.content)
        page.save(update_fields=['normalized_content'])


class Migration(migrations.Migration):

    dependencies = [
        ('lexiflux', '0016_readersettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookpage',
            name='normalized_content',
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(
            populate_normalized_content,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.AddIndex(
            model_name='bookpage',
            index=models.Index(fields=['book', 'number'], name='lexiflux_bo_book_id_2886bc_idx'),
        ),
        migrations.AddIndex(
            model_name='bookpage',
            index=models.Index(fields=['book', 'normalized_content'], name='book_normalized_content_idx'),
        ),
    ]
