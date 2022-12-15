# Generated by Django 4.1 on 2022-12-10 04:23

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ImageFile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("pubDate", models.DateTimeField(verbose_name="date published")),
                ("type", models.TextField()),
                ("dataList", models.TextField()),
                (
                    "images",
                    models.ImageField(blank=True, null=True, upload_to="images"),
                ),
            ],
        ),
    ]
