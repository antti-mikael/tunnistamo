# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-27 06:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hkijwt', '0002_api_scope'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='api',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='api',
            name='domain',
        ),
        migrations.AlterUniqueTogether(
            name='apiscope',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='apiscope',
            name='allowed_apps',
        ),
        migrations.RemoveField(
            model_name='apiscope',
            name='api',
        ),
        migrations.AlterUniqueTogether(
            name='apiscopetranslation',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='apiscopetranslation',
            name='master',
        ),
        migrations.DeleteModel(
            name='Api',
        ),
        migrations.DeleteModel(
            name='ApiDomain',
        ),
        migrations.DeleteModel(
            name='ApiScope',
        ),
        migrations.DeleteModel(
            name='ApiScopeTranslation',
        ),
    ]