import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

def test_custom_user_can_be_created():
    user = get_user_model().objects.create_user(
        username="tester",
        email="tester@example.com",
        password="secret1234",
    )
    assert user.pk
    assert user.email == "tester@example.com"
