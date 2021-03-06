# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-28 15:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mapdata', '0003_auto_20161016_1133'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='area',
            options={'verbose_name': 'Area', 'verbose_name_plural': 'Areas'},
        ),
        migrations.AlterModelOptions(
            name='building',
            options={'verbose_name': 'Building', 'verbose_name_plural': 'Buildings'},
        ),
        migrations.AlterField(
            model_name='area',
            name='level',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='areas', to='mapdata.Level', verbose_name='level'),
        ),
        migrations.AlterField(
            model_name='area',
            name='package',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='areas', to='mapdata.Package', verbose_name='map package'),
        ),
        migrations.AlterField(
            model_name='building',
            name='level',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buildings', to='mapdata.Level', verbose_name='level'),
        ),
        migrations.AlterField(
            model_name='building',
            name='package',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buildings', to='mapdata.Package', verbose_name='map package'),
        ),
    ]
