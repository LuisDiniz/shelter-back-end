from django.db import models
from adoptantes.models import Adoptante


class Animal(models.Model):
    DOG = "dog"
    CAT = "cat"

    MALE = "male"
    FEMALE = "female"

    SPECIES_CHOICES = [
        (DOG, "Cão"),
        (CAT, "Gato"),
    ]

    GENDER_CHOICES = [
        (MALE, "Macho"),
        (FEMALE, "Fêmea"),
    ]

    name = models.CharField(max_length=20)
    idade = models.IntegerField()
    cor = models.CharField(max_length=20)
    pelo = models.CharField(max_length=20)
    porte = models.CharField(max_length=20)
    raca = models.CharField(max_length=20)

    descricao = models.TextField(default="")
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICES,
        default=MALE,
    )
    medical_history = models.TextField(blank=True, default="")
    vaccinations = models.TextField(blank=True, default="")

    tipo = models.CharField(
        max_length=4,
        choices=SPECIES_CHOICES,
        default=DOG
    )

    adoptante = models.ForeignKey(Adoptante, on_delete=models.SET_NULL, null=True, blank=True)
    admission_date = models.DateField(auto_now_add=True, null=True, blank=True)
    last_update_date = models.DateField(auto_now_add=True)
    adopted_date = models.DateField(auto_now_add=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.raca}" 


class AnimalImages(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, null=True, related_name="fotos")
    image_url = models.URLField(max_length=500, blank=True, default="")

    def get_url(self, request=None):
        if self.image_url:
            return self.image_url

        return ""

    @property
    def url(self):
        return self.get_url()
