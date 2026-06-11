from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlparse, urlunparse

from django.db import migrations, models
from django.db.models import Q


CLOUDINARY_FOLDER = "Animais"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def split_cloudinary_upload_path(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split("/")

    try:
        upload_index = path_parts.index("upload")
    except ValueError:
        return parsed_url, path_parts, None, []

    return (
        parsed_url,
        path_parts,
        upload_index,
        path_parts[upload_index + 1 :],
    )


def looks_like_cloudinary_version(path_part):
    return path_part.startswith("v") and path_part[1:].isdigit()


def split_transformations_and_asset_path(after_upload_parts):
    for index, path_part in enumerate(after_upload_parts):
        if looks_like_cloudinary_version(path_part):
            return after_upload_parts[: index + 1], after_upload_parts[index + 1 :]

    if len(after_upload_parts) <= 1:
        return [], after_upload_parts

    return after_upload_parts[:-1], after_upload_parts[-1:]


def strip_image_extension(asset_name):
    path = PurePosixPath(asset_name)

    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return asset_name[: -len(path.suffix)]

    return asset_name


def normalize_cloudinary_url_and_public_id(url):
    parsed_url, path_parts, upload_index, after_upload_parts = split_cloudinary_upload_path(url)

    if upload_index is None or not after_upload_parts:
        asset_name = strip_image_extension(PurePosixPath(urlparse(url).path).name)
        return url, f"{CLOUDINARY_FOLDER}/{unquote(asset_name)}"

    transformation_parts, asset_path_parts = split_transformations_and_asset_path(after_upload_parts)

    if not asset_path_parts:
        return url, ""

    if asset_path_parts[0] != CLOUDINARY_FOLDER:
        asset_path_parts = [CLOUDINARY_FOLDER, *asset_path_parts]

    normalized_path_parts = [
        *path_parts[: upload_index + 1],
        *transformation_parts,
        *asset_path_parts,
    ]
    normalized_path = "/".join(normalized_path_parts)
    normalized_url = urlunparse(parsed_url._replace(path=normalized_path))

    asset_name = strip_image_extension(asset_path_parts[-1])
    public_id = f"{CLOUDINARY_FOLDER}/{unquote(asset_name)}"

    return normalized_url, public_id


def backfill_image_metadata(apps, schema_editor):
    image_model = apps.get_model("animais", "AnimalImages")

    for image in image_model.objects.exclude(image_url="").order_by("id"):
        image.image_url, image.cloudinary_public_id = normalize_cloudinary_url_and_public_id(
            image.image_url
        )
        image.save(update_fields=["image_url", "cloudinary_public_id"])

    animal_ids = (
        image_model.objects.exclude(image_url="")
        .values_list("animal_id", flat=True)
        .distinct()
    )

    for animal_id in animal_ids:
        cover_image = (
            image_model.objects.filter(animal_id=animal_id)
            .exclude(image_url="")
            .order_by("id")
            .first()
        )

        if cover_image:
            cover_image.is_cover = True
            cover_image.save(update_fields=["is_cover"])


def reverse_image_metadata(apps, schema_editor):
    image_model = apps.get_model("animais", "AnimalImages")
    image_model.objects.update(is_cover=False, cloudinary_public_id="")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("animais", "0006_add_missing_animal_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="animalimages",
            name="is_cover",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="animalimages",
            name="cloudinary_public_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.RunPython(backfill_image_metadata, reverse_image_metadata, atomic=True),
        migrations.AlterField(
            model_name="animalimages",
            name="cloudinary_public_id",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AddConstraint(
            model_name="animalimages",
            constraint=models.CheckConstraint(
                check=~Q(cloudinary_public_id=""),
                name="animal_image_public_id_required",
            ),
        ),
        migrations.AddConstraint(
            model_name="animalimages",
            constraint=models.UniqueConstraint(
                condition=Q(is_cover=True),
                fields=("animal",),
                name="one_cover_image_per_animal",
            ),
        ),
    ]
