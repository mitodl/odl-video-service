"""
Record whether each description is plain text or rich text.

Schema only, deliberately: there is no data migration converting the existing
plain-text descriptions to HTML. Every existing row takes the `text` default and
keeps being rendered escaped, exactly as it was before rich text existed, so
nothing already stored changes meaning and nothing can be corrupted by a
conversion that guessed wrong. Authors upgrade a description to rich text one at
a time from the edit dialog (ui.html.upgrade_description).

`ADD COLUMN ... DEFAULT <constant>` is metadata-only on PostgreSQL 11+ - the
default lands in pg_attribute rather than being written to every row - so this
runs in constant time whatever the table size, and the following DROP DEFAULT
does not rewrite either.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui', '0043_fail_stuck_uploading_videos'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='description_format',
            field=models.CharField(choices=[('text', 'Plain text'), ('html', 'Rich text')], default='text', max_length=4),
        ),
        migrations.AddField(
            model_name='video',
            name='description_format',
            field=models.CharField(choices=[('text', 'Plain text'), ('html', 'Rich text')], default='text', max_length=4),
        ),
    ]
