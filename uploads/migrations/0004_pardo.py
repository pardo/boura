# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-09-13 00:51
from __future__ import unicode_literals

from django.db import migrations, models
import django_common.db_fields
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('uploads', '0003_auto_20170906_1912'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pardo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('image', sorl.thumbnail.fields.ImageField(upload_to=b'pardos/%Y-%m-%d/')),
                ('meta', django_common.db_fields.JSONField(blank=True, default={})),
            ],
        ),
    ]