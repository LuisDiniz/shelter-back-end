import json
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from .models import Animal, AnimalImages
from .views import CloudinaryUploadError


class AnimalApiTests(TestCase):
    def setUp(self):
        cache.clear()
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
            image_url="https://res.cloudinary.com/demo/image/upload/Animais/maia.jpg",
            cloudinary_public_id="Animais/maia",
            is_cover=True,
        )

    def test_public_can_list_animals_with_new_image_contract(self):
        second_image = AnimalImages.objects.create(
            animal=self.animal,
            image_url="https://res.cloudinary.com/demo/image/upload/Animais/maia-2.jpg",
            cloudinary_public_id="Animais/maia-2",
        )

        response = self.client.get("/api/animals")
        animals = response.json()
        maia = next(animal for animal in animals if animal["name"] == "Maia")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(maia["species"], "cat")
        self.assertEqual(maia["gender"], "female")
        self.assertNotIn("image_url", maia)
        self.assertNotIn("image_urls", maia)
        self.assertEqual(maia["cover_image_url"], self.animal_image.image_url)
        self.assertEqual(
            maia["images"],
            [self.animal_image.image_url, second_image.image_url],
        )

    def test_animals_api_does_not_register_trailing_slash_urls(self):
        list_response = self.client.get("/api/animals/")
        detail_response = self.client.get(f"/api/animals/{self.animal.id}/")

        self.assertEqual(list_response.status_code, 404)
        self.assertEqual(detail_response.status_code, 404)

    def test_animal_list_api_uses_cache_after_first_request(self):
        first_response = self.client.get("/api/animals")

        with self.assertNumQueries(0):
            cached_response = self.client.get("/api/animals")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(cached_response.status_code, 200)
        self.assertEqual(cached_response.json(), first_response.json())

    def test_public_can_retrieve_animal(self):
        response = self.client.get(f"/api/animals/{self.animal.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.animal.id)
        self.assertEqual(response.json()["cover_image_url"], self.animal_image.image_url)
        self.assertEqual(response.json()["images"], [self.animal_image.image_url])
        self.assertNotIn("image_url", response.json())
        self.assertNotIn("image_urls", response.json())

    def test_animal_detail_api_uses_cache_after_first_request(self):
        first_response = self.client.get(f"/api/animals/{self.animal.id}")

        with self.assertNumQueries(0):
            cached_response = self.client.get(f"/api/animals/{self.animal.id}")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(cached_response.status_code, 200)
        self.assertEqual(cached_response.json(), first_response.json())

    def test_animal_create_invalidates_list_cache(self):
        token = self._get_token("admin@example.com", "admin-pass")
        self.client.get("/api/animals")

        with patch(
            "animais.views.upload_animal_image_to_cloudinary",
            return_value={
                "url": "https://res.cloudinary.com/demo/image/upload/Animais/max.jpg",
                "public_id": "Animais/max",
            },
        ):
            create_response = self.client.post(
                "/api/animals",
                data={
                    **self._animal_payload(),
                    "images": json.dumps([
                        {"file_key": "image_0", "is_cover": True},
                    ]),
                    "image_0": self._uploaded_file("max.jpg"),
                },
                headers={"Authorization": f"Token {token}"},
            )
        list_response = self.client.get("/api/animals")
        animal_names = [animal["name"] for animal in list_response.json()]

        self.assertEqual(create_response.status_code, 201)
        self.assertIn("Max", animal_names)

    def test_animal_update_and_delete_invalidate_cached_api_responses(self):
        token = self._get_token("admin@example.com", "admin-pass")
        self.client.get("/api/animals")
        self.client.get(f"/api/animals/{self.animal.id}")

        update_response = self.client.patch(
            f"/api/animals/{self.animal.id}",
            data=json.dumps({"name": "Maia Updated"}),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )
        list_response = self.client.get("/api/animals")
        detail_response = self.client.get(f"/api/animals/{self.animal.id}")

        self.assertEqual(update_response.status_code, 200)
        self.assertIn(
            "Maia Updated",
            [animal["name"] for animal in list_response.json()],
        )
        self.assertEqual(detail_response.json()["name"], "Maia Updated")

        delete_response = self.client.delete(
            f"/api/animals/{self.animal.id}",
            headers={"Authorization": f"Token {token}"},
        )
        list_after_delete_response = self.client.get("/api/animals")
        detail_after_delete_response = self.client.get(f"/api/animals/{self.animal.id}")

        self.assertEqual(delete_response.status_code, 204)
        self.assertNotIn(
            self.animal.id,
            [animal["id"] for animal in list_after_delete_response.json()],
        )
        self.assertEqual(detail_after_delete_response.status_code, 404)

    def test_anonymous_user_cannot_create_animal(self):
        response = self.client.post(
            "/api/animals",
            data=json.dumps(self._animal_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_authenticated_non_admin_cannot_create_animal(self):
        token = self._get_token("user@example.com", "user-pass")

        response = self.client.post(
            "/api/animals",
            data=json.dumps(self._animal_payload()),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_animal_with_multiple_uploaded_images(self):
        token = self._get_token("admin@example.com", "admin-pass")

        with patch(
            "animais.views.upload_animal_image_to_cloudinary",
            side_effect=[
                {
                    "url": "https://res.cloudinary.com/demo/image/upload/Animais/max-1.jpg",
                    "public_id": "Animais/max-1",
                },
                {
                    "url": "https://res.cloudinary.com/demo/image/upload/Animais/max-2.jpg",
                    "public_id": "Animais/max-2",
                },
            ],
        ) as upload_mock:
            response = self.client.post(
                "/api/animals",
                data={
                    **self._animal_payload(),
                    "images": json.dumps([
                        {"file_key": "image_0", "is_cover": False},
                        {"file_key": "image_1", "is_cover": True},
                    ]),
                    "image_0": self._uploaded_file("max-1.jpg"),
                    "image_1": self._uploaded_file("max-2.jpg"),
                },
                headers={"Authorization": f"Token {token}"},
            )

        self.assertEqual(response.status_code, 201)
        upload_mock.assert_has_calls([
            call(self._any_uploaded_file()),
            call(self._any_uploaded_file()),
        ])
        self.assertEqual(
            response.json()["images"],
            [
                "https://res.cloudinary.com/demo/image/upload/Animais/max-2.jpg",
                "https://res.cloudinary.com/demo/image/upload/Animais/max-1.jpg",
            ],
        )
        self.assertEqual(
            response.json()["cover_image_url"],
            "https://res.cloudinary.com/demo/image/upload/Animais/max-2.jpg",
        )
        self.assertTrue(
            AnimalImages.objects.filter(
                animal_id=response.json()["id"],
                cloudinary_public_id="Animais/max-2",
                is_cover=True,
            ).exists()
        )

    def test_update_manifest_adds_removes_and_changes_cover(self):
        token = self._get_token("admin@example.com", "admin-pass")
        second_image = AnimalImages.objects.create(
            animal=self.animal,
            image_url="https://res.cloudinary.com/demo/image/upload/Animais/maia-2.jpg",
            cloudinary_public_id="Animais/maia-2",
        )

        with (
            patch(
                "animais.views.upload_animal_image_to_cloudinary",
                return_value={
                    "url": "https://res.cloudinary.com/demo/image/upload/Animais/maia-3.jpg",
                    "public_id": "Animais/maia-3",
                },
            ) as upload_mock,
            patch("animais.views.delete_animal_image_from_cloudinary") as delete_mock,
        ):
            response = self.client.generic(
                "PATCH",
                f"/api/animals/{self.animal.id}",
                data=encode_multipart(
                    BOUNDARY,
                    {
                        "images": json.dumps([
                            {"url": second_image.image_url, "is_cover": True},
                            {"file_key": "image_0", "is_cover": False},
                        ]),
                        "image_0": self._uploaded_file("maia-3.webp", "image/webp"),
                    },
                ),
                content_type=MULTIPART_CONTENT,
                headers={"Authorization": f"Token {token}"},
            )

        self.assertEqual(response.status_code, 200)
        upload_mock.assert_called_once()
        delete_mock.assert_called_once_with("Animais/maia")
        self.assertFalse(AnimalImages.objects.filter(id=self.animal_image.id).exists())
        self.assertEqual(response.json()["cover_image_url"], second_image.image_url)
        self.assertEqual(
            set(response.json()["images"]),
            {
                second_image.image_url,
                "https://res.cloudinary.com/demo/image/upload/Animais/maia-3.jpg",
            },
        )

    def test_update_fails_when_existing_manifest_url_is_not_stored(self):
        token = self._get_token("admin@example.com", "admin-pass")

        response = self.client.patch(
            f"/api/animals/{self.animal.id}",
            data=json.dumps({
                "images": [
                    {
                        "url": "https://res.cloudinary.com/demo/image/upload/Animais/missing.jpg",
                        "is_cover": True,
                    },
                ],
            }),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Existing image URL", response.json()["detail"])

    def test_update_fails_and_keeps_db_when_cloudinary_delete_fails(self):
        token = self._get_token("admin@example.com", "admin-pass")
        second_image = AnimalImages.objects.create(
            animal=self.animal,
            image_url="https://res.cloudinary.com/demo/image/upload/Animais/maia-2.jpg",
            cloudinary_public_id="Animais/maia-2",
        )

        with patch(
            "animais.views.delete_animal_image_from_cloudinary",
            side_effect=CloudinaryUploadError("Image delete failed."),
        ):
            response = self.client.patch(
                f"/api/animals/{self.animal.id}",
                data=json.dumps({
                    "images": [
                        {"url": second_image.image_url, "is_cover": True},
                    ],
                }),
                content_type="application/json",
                headers={"Authorization": f"Token {token}"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(AnimalImages.objects.filter(id=self.animal_image.id).exists())
        self.assertTrue(
            AnimalImages.objects.get(id=self.animal_image.id).is_cover
        )

    def test_rejects_legacy_image_fields(self):
        token = self._get_token("admin@example.com", "admin-pass")

        json_response = self.client.post(
            "/api/animals",
            data=json.dumps({
                **self._animal_payload(),
                "image_url": "https://res.cloudinary.com/demo/image/upload/max.jpg",
            }),
            content_type="application/json",
            headers={"Authorization": f"Token {token}"},
        )
        multipart_response = self.client.post(
            "/api/animals",
            data={
                **self._animal_payload(),
                "image_file": self._uploaded_file("max.jpg"),
            },
            headers={"Authorization": f"Token {token}"},
        )

        self.assertEqual(json_response.status_code, 400)
        self.assertEqual(multipart_response.status_code, 400)
        self.assertIn("Legacy image fields", json_response.json()["detail"])
        self.assertIn("Legacy image fields", multipart_response.json()["detail"])

    def test_rejects_manifest_without_exactly_one_cover(self):
        token = self._get_token("admin@example.com", "admin-pass")

        response = self.client.post(
            "/api/animals",
            data={
                **self._animal_payload(),
                "images": json.dumps([
                    {"file_key": "image_0", "is_cover": False},
                    {"file_key": "image_1", "is_cover": False},
                ]),
                "image_0": self._uploaded_file("max-1.jpg"),
                "image_1": self._uploaded_file("max-2.jpg"),
            },
            headers={"Authorization": f"Token {token}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("exactly one cover", response.json()["detail"])

    def test_animal_image_public_id_is_required_and_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnimalImages.objects.create(
                    animal=self.animal,
                    image_url="https://res.cloudinary.com/demo/image/upload/Animais/blank.jpg",
                    cloudinary_public_id="",
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnimalImages.objects.create(
                    animal=self.animal,
                    image_url="https://res.cloudinary.com/demo/image/upload/Animais/duplicate.jpg",
                    cloudinary_public_id=self.animal_image.cloudinary_public_id,
                )

    def test_heic_uploaded_image_is_allowed(self):
        image = SimpleUploadedFile("photo.HEIC", b"image-bytes", content_type="image/heic")

        from .views import validate_animal_image_file

        validate_animal_image_file(image)

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
            "medical_history": "Sem problemas conhecidos",
            "vaccinations": "Raiva",
        }

    def _uploaded_file(self, name, content_type="image/jpeg"):
        return SimpleUploadedFile(name, b"image-bytes", content_type=content_type)

    def _any_uploaded_file(self):
        from unittest.mock import ANY

        return ANY
