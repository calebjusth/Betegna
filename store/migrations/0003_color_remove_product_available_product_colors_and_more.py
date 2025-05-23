# Generated by Django 5.2 on 2025-04-29 10:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_product_available'),
    ]

    operations = [
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('hex_code', models.CharField(help_text='Hex color code (e.g. #FF0000)', max_length=7)),
                ('css_class', models.CharField(blank=True, help_text='Optional CSS class for styling', max_length=50)),
            ],
            options={
                'verbose_name': 'Product Color',
                'verbose_name_plural': 'Product Colors',
                'ordering': ['name'],
            },
        ),
        migrations.RemoveField(
            model_name='product',
            name='available',
        ),
        migrations.AddField(
            model_name='product',
            name='colors',
            field=models.ManyToManyField(blank=True, help_text='Select available colors for this product', related_name='products', to='store.color'),
        ),
        migrations.AddField(
            model_name='product',
            name='primary_color',
            field=models.ForeignKey(blank=True, help_text='Main color to display in listings', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_color_products', to='store.color'),
        ),
    ]
