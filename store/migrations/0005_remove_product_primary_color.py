# Generated by Django 5.2 on 2025-04-29 10:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_remove_color_css_class_remove_color_hex_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='primary_color',
        ),
    ]
