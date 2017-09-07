# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-06 19:12
from __future__ import unicode_literals

from django.db import migrations
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('uploads', '0002_entity_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entity',
            name='image',
            field=sorl.thumbnail.fields.ImageField(blank=True, null=True, upload_to='crops/%Y-%m-%d/'),
        ),
        migrations.AlterField(
            model_name='upload',
            name='image',
            field=sorl.thumbnail.fields.ImageField(upload_to='uploads/%Y-%m-%d/'),
        ),
    ]