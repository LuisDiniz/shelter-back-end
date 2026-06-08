import json

from django.contrib.auth import get_user_model
from django.test import TestCase


class AuthTokenApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            email="admin@example.com",
            password="admin-pass",
            is_staff=True,
        )

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

    def test_token_endpoint_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/token/",
            data=json.dumps({"username": "admin@example.com", "password": "wrong-pass"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid credentials.")
