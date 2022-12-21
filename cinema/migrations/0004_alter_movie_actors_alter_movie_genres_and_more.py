# Generated by Django 4.1 on 2022-12-21 15:34

import cinema.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cinema", "0003_alter_movie_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="movie",
            name="actors",
            field=models.ManyToManyField(blank=True, to="cinema.actor"),
        ),
        migrations.AlterField(
            model_name="movie",
            name="genres",
            field=models.ManyToManyField(blank=True, to="cinema.genre"),
        ),
        migrations.AlterField(
            model_name="movie",
            name="image",
            field=models.ImageField(
                null=True, upload_to=cinema.models.movie_image_file_path
            ),
        ),
    ]
