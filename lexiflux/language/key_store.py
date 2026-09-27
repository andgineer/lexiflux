import base64
import re
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from django.apps import apps
from django.utils.crypto import salted_hmac

_SCOPE = re.compile(r"u-(\d+)")


def scope_of(user_id: int) -> str:
    return f"u-{user_id}"


def user_of(scope: str) -> int | None:
    match = _SCOPE.fullmatch(scope)
    return int(match.group(1)) if match else None


def _fernet() -> Fernet:
    digest = salted_hmac("lexiflux.ai-keys", "fernet", algorithm="sha256").digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def _keys() -> Any:
    return apps.get_model("lexiflux", "AIKey").objects


def own_key(user_id: int, ref: str) -> str | None:
    token = _keys().filter(user_id=user_id, ref=ref).values_list("encrypted", flat=True).first()
    return _decrypt(token) if token is not None else None


def own_keys(user_id: int) -> dict[str, str]:
    keys = {}
    for ref, token in _keys().filter(user_id=user_id).values_list("ref", "encrypted"):
        value = _decrypt(token)
        if value is not None:
            keys[ref] = value
    return keys


def scoped_refs() -> frozenset[str]:
    return frozenset(
        f"{scope_of(user_id)}/{ref}" for user_id, ref in _keys().values_list("user_id", "ref")
    )


def save_own_key(user: Any, ref: str, value: str) -> None:
    encrypted = _fernet().encrypt(value.encode()).decode()
    _keys().update_or_create(user=user, ref=ref, defaults={"encrypted": encrypted})


def clear_own_key(user: Any, ref: str) -> None:
    _keys().filter(user=user, ref=ref).delete()
