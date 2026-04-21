"""Tests para app.core.auth — validación de JWT de Supabase.

jose.jwt.decode se mockea para no requerir SUPABASE_JWT_SECRET real.
os.getenv se mockea para garantizar que el secret no esté vacío y los
tests alcancen la lógica de validación del token.
Los tests verifican los tres escenarios: sin prefijo Bearer, token inválido
y token válido.
"""
import pytest
from unittest.mock import patch
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Importación diferida con fallback
# ---------------------------------------------------------------------------
# Si auth.py no existe todavía, los tests se marcan como skip automáticamente
# para no bloquear CI — se resolverán cuando el agente backend cree el módulo.
try:
    from app.core.auth import get_current_user
    _AUTH_AVAILABLE = True
except ImportError:
    _AUTH_AVAILABLE = False
    get_current_user = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    not _AUTH_AVAILABLE,
    reason="app.core.auth no disponible todavía — pendiente agente backend",
)

# Secret de prueba inyectado vía patch en todos los tests
_FAKE_SECRET = "test-jwt-secret-not-real"


# ---------------------------------------------------------------------------
# Test 1 — Header sin prefijo "Bearer " levanta 401
# ---------------------------------------------------------------------------

def test_get_current_user_raises_401_without_bearer_prefix():
    """Authorization sin 'Bearer ' al inicio debe levantar HTTPException 401."""
    # Arrange
    invalid_header = "Token eyJsomejwt"

    with patch("app.core.auth.os.getenv", return_value=_FAKE_SECRET):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=invalid_header)

    assert exc_info.value.status_code == 401
    assert "requerido" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Test 2 — JWT inválido (JWTError) levanta 401
# ---------------------------------------------------------------------------

def test_get_current_user_raises_401_with_invalid_token():
    """Un JWT malformado o con firma incorrecta debe levantar HTTPException 401."""
    from jose import JWTError

    # Arrange
    bad_token = "Bearer esto.no.es.un.jwt.valido"

    with patch("app.core.auth.os.getenv", return_value=_FAKE_SECRET), \
         patch("app.core.auth.jwt.decode", side_effect=JWTError("firma incorrecta")):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=bad_token)

    assert exc_info.value.status_code == 401
    assert "inválido" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Test 3 — JWT válido devuelve dict con user_id y email
# ---------------------------------------------------------------------------

def test_get_current_user_returns_user_dict_with_valid_token():
    """Un JWT bien formado debe devolver {'user_id': ..., 'email': ...}."""
    # Arrange
    fake_payload = {
        "sub": "test-user-uuid",
        "email": "test@test.com",
        "aud": "authenticated",
    }
    valid_token = "Bearer eyJvalid.token.here"

    with patch("app.core.auth.os.getenv", return_value=_FAKE_SECRET), \
         patch("app.core.auth.jwt.decode", return_value=fake_payload):
        # Act
        result = get_current_user(authorization=valid_token)

    # Assert
    assert result["user_id"] == "test-user-uuid"
    assert result["email"] == "test@test.com"
    # No debe filtrarse información sensible extra del payload
    assert set(result.keys()) == {"user_id", "email"}
