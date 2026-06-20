from urllib.parse import urlparse, urlunparse

from django.db import migrations


CLOUDINARY_FOLDER = "Animais"


def remove_cloudinary_folder_from_url(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split("/")

    try:
        upload_index = path_parts.index("upload")
    except ValueError:
        return url

    after_upload_parts = path_parts[upload_index + 1 :]
    if CLOUDINARY_FOLDER not in after_upload_parts:
        return url

    cleaned_parts = [part for part in after_upload_parts if part != CLOUDINARY_FOLDER]
    if cleaned_parts == after_upload_parts:
        return url

    normalized_path = "/".join([*path_parts[: upload_index + 1], *cleaned_parts])
    return urlunparse(parsed_url._replace(path=normalized_path))


def remove_cloudinary_folder(apps, schema_editor):
    image_model = apps.get_model("animais", "AnimalImages")

    for image in image_model.objects.exclude(image_url=""):
        cleaned_url = remove_cloudinary_folder_from_url(image.image_url)
        if cleaned_url != image.image_url:
            image.image_url = cleaned_url
            image.save(update_fields=["image_url"])


def restore_cloudinary_folder(apps, schema_editor):
    image_model = apps.get_model("animais", "AnimalImages")

    for image in image_model.objects.exclude(image_url=""):
        parsed_url = urlparse(image.image_url)
        path_parts = parsed_url.path.split("/")

        try:
            upload_index = path_parts.index("upload")
        except ValueError:
            continue

        after_upload_parts = path_parts[upload_index + 1 :]
        if CLOUDINARY_FOLDER in after_upload_parts:
            continue

        normalized_path = "/".join(
            [*path_parts[: upload_index + 1], CLOUDINARY_FOLDER, *after_upload_parts]
        )
        image.image_url = urlunparse(parsed_url._replace(path=normalized_path))
        image.save(update_fields=["image_url"])


class Migration(migrations.Migration):
    dependencies = [
        ("animais", "0007_add_cover_and_public_id_to_animalimages"),
    ]

    operations = [
        migrations.RunPython(remove_cloudinary_folder, restore_cloudinary_folder),
    ]
