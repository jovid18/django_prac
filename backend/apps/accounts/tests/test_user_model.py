import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.models import SocialAccount

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_username_field_is_email():
    """username を捨てて email をログイン ID にしている（docs/04-data-model.md）。"""
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []


def test_create_user_with_password():
    user = User.objects.create_user(email="taro@example.com", password="correct-horse-battery")

    assert user.has_usable_password()
    assert user.check_password("correct-horse-battery")
    assert user.is_active
    assert not user.is_staff


def test_social_only_user_has_no_usable_password():
    """Google のみのユーザーはパスワードを持たない。"""
    user = User.objects.create_user(email="social@example.com")

    assert not user.has_usable_password()


def test_create_superuser():
    user = User.objects.create_superuser(email="admin@example.com", password="admin-password-x")

    assert user.is_staff
    assert user.is_superuser


def test_email_must_be_unique():
    User.objects.create_user(email="dup@example.com", password="pw-that-is-long-enough")

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="dup@example.com", password="pw-that-is-long-enough")


def test_email_is_required():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="pw-that-is-long-enough")


def test_same_provider_uid_cannot_be_registered_twice():
    """provider + provider_uid に UNIQUE 制約。"""
    a = User.objects.create_user(email="a@example.com")
    b = User.objects.create_user(email="b@example.com")

    SocialAccount.objects.create(
        user=a, provider=SocialAccount.Provider.GOOGLE, provider_uid="sub-1"
    )

    with pytest.raises(IntegrityError):
        SocialAccount.objects.create(
            user=b, provider=SocialAccount.Provider.GOOGLE, provider_uid="sub-1"
        )


def test_user_can_have_multiple_social_accounts():
    """1 ユーザーが ID/PW と複数プロバイダを併せ持てる設計。"""
    user = User.objects.create_user(email="multi@example.com", password="pw-that-is-long-enough")
    SocialAccount.objects.create(
        user=user, provider=SocialAccount.Provider.GOOGLE, provider_uid="sub-2"
    )

    assert user.social_accounts.count() == 1
    assert user.has_usable_password()
