# Generated by Django 3.2.13 on 2022-11-14 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='search',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_count', models.IntegerField(default=0)),
                ('search_text', models.CharField(max_length=20)),
            ],
        ),
    ]