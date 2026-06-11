from django.db import migrations


MISSING_ANIMAL_IMAGES = [
    (
        2,
        "https://res.cloudinary.com/dlqmc28to/image/upload/v1773878172/Evaristo1_i5og24.jpg",
    ),
    (
        4,
        "https://res.cloudinary.com/dlqmc28to/image/upload/v1773838716/IMG_2720_ukzsdz.jpg",
    ),
    (
        5,
        "https://res.cloudinary.com/dlqmc28to/image/upload/v1765875774/Palhacinho_fhrbhq.jpg",
    ),
    (
        6,
        "https://res.cloudinary.com/dlqmc28to/image/upload/v1765876377/Manny_ccbyjz.jpg",
    ),
]


def add_missing_animal_images(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")
    image_model = apps.get_model("animais", "AnimalImages")

    for animal_id, image_url in MISSING_ANIMAL_IMAGES:
        try:
            animal = animal_model.objects.get(id=animal_id)
        except animal_model.DoesNotExist:
            continue

        image_model.objects.get_or_create(
            animal=animal,
            image_url=image_url,
        )


def remove_missing_animal_images(apps, schema_editor):
    image_model = apps.get_model("animais", "AnimalImages")
    image_urls = [image_url for _, image_url in MISSING_ANIMAL_IMAGES]
    image_model.objects.filter(image_url__in=image_urls).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("animais", "0005_move_image_urls_to_animal_images"),
    ]

    operations = [
        migrations.RunPython(add_missing_animal_images, remove_missing_animal_images),
    ]
