import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Animal


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
            image_url="https://res.cloudinary.com/demo/image/upload/maia.jpg",
            medical_history="Saudável",
            vaccinations="Raiva",
        )

    def test_public_can_list_animals(self):
        response = self.client.get("/api/animals/")
        animals = response.json()
        maia = next(animal for animal in animals if animal["name"] == "Maia")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(maia["species"], "cat")
        self.assertEqual(maia["gender"], "female")
        self.assertIn("image_url", maia)

    def test_public_can_retrieve_animal(self):
        response = self.client.get(f"/api/animals/{self.animal.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.animal.id)
        self.assertEqual(response.json()["image_url"], self.animal.image_url)

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

        animal_id = create_response.json()["id"]
        update_response = self.client.patch(
            f"/api/animals/{animal_id}/",
            data=json.dumps({"name": "Max Updated"}),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "Max Updated")

        delete_response = self.client.delete(
            f"/api/animals/{animal_id}/",
            headers={"Authorization": f"Token {token}"},
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_token_endpoint_returns_token_and_user(self):
        response = self.client.post(
            "/api/auth/token/",
            data=json.dumps({"username": "admin@example.com", "password": "admin-pass"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())
        self.assertEqual(response.json()["user"]["username"], "admin@example.com")
        self.assertEqual(response.json()["user"]["role"], "admin")

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
