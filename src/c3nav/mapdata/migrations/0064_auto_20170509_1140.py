# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-09 11:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mapdata', '0063_auto_20170508_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='space',
            name='category',
            field=models.CharField(choices=[('', 'normal'), ('stairs', 'stairs'), ('escalator', 'escalator'), ('elevator', 'elevator')], default='', max_length=16, verbose_name='category'),
        ),
        migrations.AlterField(
            model_name='space',
            name='layer',
            field=models.CharField(choices=[('', 'normal'), ('upper', 'upper'), ('lower', 'lower')], default='', max_length=16, verbose_name='level'),
        ),
    ]
