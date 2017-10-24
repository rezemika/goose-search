# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-10-24 16:07
from __future__ import unicode_literals

from django.db import migrations, models
import search.models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Nom')),
                ('processing_rules', models.TextField(blank=True, null=True, validators=[search.models.filter_pr_validator], verbose_name='Règles de traitement')),
            ],
            options={
                'verbose_name_plural': 'Filtres',
                'verbose_name': 'Filtre',
            },
        ),
        migrations.AlterModelOptions(
            name='searchpreset',
            options={'verbose_name': "Point d'intérêt", 'verbose_name_plural': "Points d'intérêt"},
        ),
        migrations.AddField(
            model_name='searchpreset',
            name='name_en',
            field=models.CharField(max_length=50, null=True, verbose_name='Nom'),
        ),
        migrations.AddField(
            model_name='searchpreset',
            name='name_fr',
            field=models.CharField(max_length=50, null=True, verbose_name='Nom'),
        ),
        migrations.AddField(
            model_name='searchpreset',
            name='processing_rules_en',
            field=models.TextField(blank=True, null=True, validators=[search.models.preset_pr_validator], verbose_name='Règles de traitement'),
        ),
        migrations.AddField(
            model_name='searchpreset',
            name='processing_rules_fr',
            field=models.TextField(blank=True, null=True, validators=[search.models.preset_pr_validator], verbose_name='Règles de traitement'),
        ),
        migrations.AlterField(
            model_name='searchpreset',
            name='name',
            field=models.CharField(max_length=50, verbose_name='Nom'),
        ),
        migrations.AlterField(
            model_name='searchpreset',
            name='osm_keys',
            field=models.TextField(blank=True, null=True, validators=[search.models.osm_keys_validator], verbose_name='Clés OpenStreetMap'),
        ),
        migrations.AlterField(
            model_name='searchpreset',
            name='processing_rules',
            field=models.TextField(blank=True, null=True, validators=[search.models.preset_pr_validator], verbose_name='Règles de traitement'),
        ),
        migrations.AddField(
            model_name='searchpreset',
            name='filters',
            field=models.ManyToManyField(related_name='search_presets', to='search.Filter'),
        ),
    ]
