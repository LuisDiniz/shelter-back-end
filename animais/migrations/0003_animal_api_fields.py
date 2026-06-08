from django.db import migrations, models


def normalize_species_and_dates(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")

    for animal in animal_model.objects.all():
        updates = []

        if animal.tipo == "cao":
            animal.tipo = "dog"
            updates.append("tipo")
        elif animal.tipo == "gato":
            animal.tipo = "cat"
            updates.append("tipo")

        if not animal.admission_date:
            animal.admission_date = animal.last_update_date
            updates.append("admission_date")

        if updates:
            animal.save(update_fields=updates)


def restore_species(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")

    for animal in animal_model.objects.all():
        updates = []

        if animal.tipo == "dog":
            animal.tipo = "cao"
            updates.append("tipo")
        elif animal.tipo == "cat":
            animal.tipo = "gato"
            updates.append("tipo")

        if updates:
            animal.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("animais", "0002_alter_animalimages_imagem"),
    ]

    operations = [
        migrations.AddField(
            model_name="animal",
            name="image_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="animal",
            name="gender",
            field=models.CharField(
                choices=[("male", "Macho"), ("female", "Fêmea")],
                default="male",
                max_length=6,
            ),
        ),
        migrations.AddField(
            model_name="animal",
            name="medical_history",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="animal",
            name="vaccinations",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="animal",
            name="admission_date",
            field=models.DateField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.RunPython(normalize_species_and_dates, restore_species),
        migrations.AlterField(
            model_name="animal",
            name="tipo",
            field=models.CharField(
                choices=[("dog", "Cão"), ("cat", "Gato")],
                default="dog",
                max_length=4,
            ),
        ),
    ]
