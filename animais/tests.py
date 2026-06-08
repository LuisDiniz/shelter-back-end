import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Animal, AnimalImages


class AnimalApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            email="admin@example.com",
            password="admin-pass",
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            email="user@example.com",
            password="user-pass",
        )
        self.animal = Animal.objects.create(
            name="Maia",
            idade=1,
            cor="Preto",
            pelo="Curto",
            porte="Pequeno",
            raca="Europeu",
            descricao="Gata meiga para adoção.",
            tipo=Animal.CAT,
            gender=Animal.FEMALE,
            medical_history="Saudável",
            vaccinations="Raiva",
        )
        self.animal_image = AnimalImages.objects.create(
            animal=self.animal,
            image_url="https://res.cloudinary.com/demo/image/upload/maia.jpg",
        )

    def test_public_can_list_animals(self):
        response = self.client.get("/api/animals/")
        animals = response.json()
        maia = next(animal for animal in animals if animal["name"] == "Maia")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(maia["species"], "cat")
        self.assertEqual(maia["gender"], "female")
        self.assertIn("image_url", maia)
        self.assertIn(self.animal_image.image_url, maia["image_urls"])

    def test_public_can_retrieve_animal(self):
        response = self.client.get(f"/api/animals/{self.animal.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.animal.id)
        self.assertEqual(response.json()["image_url"], self.animal_image.image_url)
        self.assertEqual(response.json()["images"][0]["image_url"], self.animal_image.image_url)

    def test_anonymous_user_cannot_create_animal(self):
        response = self.client.post(
            "/api/animals/",
            data=json.dumps(self._animal_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_authenticated_non_admin_cannot_create_animal(self):
        token = self._get_token("user@example.com", "user-pass")

        response = self.client.post(
            "/api/animals/",
            data=json.dumps(self._animal_payload()),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_update_and_delete_animal(self):
        token = self._get_token("admin@example.com", "admin-pass")

        create_response = self.client.post(
            "/api/animals/",
            data=json.dumps(self._animal_payload()),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["species"], "dog")
        self.assertEqual(create_response.json()["image_url"], self._animal_payload()["image_url"])

        animal_id = create_response.json()["id"]
        self.assertTrue(
            AnimalImages.objects.filter(
                animal_id=animal_id,
                image_url=self._animal_payload()["image_url"],
            ).exists()
        )
        update_response = self.client.patch(
            f"/api/animals/{animal_id}/",
            data=json.dumps({
                "name": "Max Updated",
                "image_url": "https://res.cloudinary.com/demo/image/upload/max-2.jpg",
            }),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "Max Updated")
        self.assertIn(
            "https://res.cloudinary.com/demo/image/upload/max-2.jpg",
            update_response.json()["image_urls"],
        )

        delete_response = self.client.delete(
            f"/api/animals/{animal_id}/",
            headers={"Authorization": f"Token {token}"},
        )
        self.assertEqual(delete_response.status_code, 204)

    def _get_token(self, username, password):
        response = self.client.post(
            "/api/auth/token/",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )
        return response.json()["token"]

    def _animal_payload(self):
        return {
            "name": "Max",
            "species": "dog",
            "breed": "Labrador",
            "age": 4,
            "gender": "male",
            "description": "Cão enérgico para adoção.",
            "image_url": "https://res.cloudinary.com/demo/image/upload/max.jpg",
            "medical_history": "Sem problemas conhecidos",
            "vaccinations": "Raiva",
        }
