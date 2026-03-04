# Migration to switch from jsonfield.JSONField to django.db.models.JSONField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms_named_menus', '0008_auto_20200522_2039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cmsnamedmenu',
            name='pages',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]

