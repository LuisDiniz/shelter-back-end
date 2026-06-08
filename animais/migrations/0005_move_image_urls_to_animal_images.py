from django.db import migrations, models


def move_image_urls_to_animal_images(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")
    image_model = apps.get_model("animais", "AnimalImages")

    for animal in animal_model.objects.exclude(image_url=""):
        if image_model.objects.filter(animal=animal, image_url=animal.image_url).exists():
            continue

        image_model.objects.create(
            animal=animal,
            imagem="",
            image_url=animal.image_url,
        )


def restore_animal_image_urls(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")
    image_model = apps.get_model("animais", "AnimalImages")

    for animal in animal_model.objects.all():
        image = (
            image_model.objects.filter(animal=animal)
            .exclude(image_url="")
            .order_by("id")
            .first()
        )
        if image:
            animal.image_url = image.image_url
            animal.save(update_fields=["image_url"])


class Migration(migrations.Migration):
    dependencies = [
        ("animais", "0004_seed_mock_animals"),
    ]

    operations = [
        migrations.AddField(
            model_name="animalimages",
            name="image_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="animalimages",
            name="imagem",
            field=models.ImageField(blank=True, default="", upload_to="%Y/%m/%d"),
        ),
        migrations.RunPython(
            move_image_urls_to_animal_images,
            restore_animal_image_urls,
        ),
        migrations.RemoveField(
            model_name="animalimages",
            name="imagem",
        ),
        migrations.RemoveField(
            model_name="animal",
            name="comportamento_animais",
        ),
        migrations.RemoveField(
            model_name="animal",
            name="comportamento_pessoas",
        ),
        migrations.RemoveField(
            model_name="animal",
            name="image_url",
        ),
        migrations.RemoveField(
            model_name="animal",
            name="informacao_extra",
        ),
    ]
