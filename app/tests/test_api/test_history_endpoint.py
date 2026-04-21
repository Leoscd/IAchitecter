"""Tests para endpoints de historial de conversaciones (GET/POST /history).

Los tests mockean get_current_user via app.dependency_overrides para evitar
verificación real de JWT. El cliente Supabase se mockea con patch para no
necesitar DB real.

Si app.api.history no existe todavía, todos los tests se marcan como skip
automáticamente para no bloquear CI.
"""
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Verificar disponibilidad del módulo history antes de importar app.main
# ---------------------------------------------------------------------------
try:
    import importlib
    importlib.import_module("app.api.history")
    _HISTORY_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _HISTORY_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _HISTORY_AVAILABLE,
    reason="app.api.history no disponible todavía — pendiente agente backend",
)

if _HISTORY_AVAILABLE:
    from fastapi.testclient import TestClient
    from app.main import app
else:
    # Placeholder para que el módulo sea sintácticamente válido
    app = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Usuario de prueba devuelto por el override de autenticación
# ---------------------------------------------------------------------------
FAKE_USER = {"user_id": "test-user-uuid", "email": "test@test.com"}


def _fake_get_current_user():
    """Reemplaza get_current_user con una función que devuelve FAKE_USER."""
    return FAKE_USER


# ---------------------------------------------------------------------------
# Helpers de mock Supabase
# ---------------------------------------------------------------------------

def _mock_supabase_list(data: list) -> MagicMock:
    """Mockea get_client().table().select().eq().order().execute() → data."""
    mock_client = MagicMock()
    (
        mock_client.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value.data
    ) = data
    return mock_client


def _mock_supabase_insert(returned_row: dict) -> MagicMock:
    """Mockea get_client().table().insert().execute() → [returned_row]."""
    mock_client = MagicMock()
    (
        mock_client.table.return_value
        .insert.return_value
        .execute.return_value.data
    ) = [returned_row]
    return mock_client


def _mock_supabase_select_single(data: list) -> MagicMock:
    """Mockea get_client().table().select().eq().eq().execute() → data.

    Usado para buscar una conversación filtrando por id Y user_id.
    """
    mock_client = MagicMock()
    (
        mock_client.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value.data
    ) = data
    return mock_client


def _mock_supabase_messages_insert(conv_data: list, msg_returned: dict) -> MagicMock:
    """Mock para POST /history/{id}/messages.

    Primera llamada verifica que la conversación existe (pertenece al usuario),
    segunda inserta el mensaje.
    """
    mock_client = MagicMock()

    # Verificar conversación del usuario
    check_query = MagicMock()
    check_query.execute.return_value.data = conv_data

    # Insertar mensaje
    insert_query = MagicMock()
    insert_query.execute.return_value.data = [msg_returned]

    table_mock = MagicMock()
    table_mock.select.return_value.eq.return_value.eq.return_value = check_query
    table_mock.insert.return_value = insert_query

    mock_client.table.return_value = table_mock
    return mock_client


# ---------------------------------------------------------------------------
# Fixture: cliente con auth override activo
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client():
    """TestClient con dependency_override para get_current_user."""
    from app.core.auth import get_current_user

    app.dependency_overrides[get_current_user] = _fake_get_current_user

    client = TestClient(app, raise_server_exceptions=False)
    yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1 — GET /history sin token devuelve 401
# ---------------------------------------------------------------------------

def test_list_conversations_returns_401_without_token():
    """GET /history sin header Authorization debe devolver 401."""
    # Arrange — cliente sin override de auth (comportamiento real)
    client = TestClient(app, raise_server_exceptions=False)

    # Act
    resp = client.get("/api/v1/history")

    # Assert
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 2 — GET /history con token mockeado devuelve 200 y lista vacía
# ---------------------------------------------------------------------------

def test_list_conversations_returns_200_with_valid_token(auth_client):
    """GET /history con usuario autenticado devuelve 200 y lista de conversaciones."""
    # Arrange
    with patch("app.api.history.get_client", return_value=_mock_supabase_list([])):
        # Act
        resp = auth_client.get("/api/v1/history")

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert "conversations" in body
    assert isinstance(body["conversations"], list)


# ---------------------------------------------------------------------------
# Test 3 — POST /history con body válido devuelve 201
# ---------------------------------------------------------------------------

def test_create_conversation_returns_201(auth_client):
    """POST /history con project_id crea conversación y devuelve 201."""
    # Arrange
    new_conv = {
        "id": "conv-uuid-001",
        "project_id": "p1",
        "user_id": FAKE_USER["user_id"],
        "created_at": "2026-04-21T10:00:00",
    }
    with patch("app.api.history.get_client", return_value=_mock_supabase_insert(new_conv)):
        # Act
        resp = auth_client.post("/api/v1/history", json={"project_id": "p1"})

    # Assert
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "conv-uuid-001"
    assert body["project_id"] == "p1"


# ---------------------------------------------------------------------------
# Test 4 — GET /history/{id} con conversación de otro usuario devuelve 404
# ---------------------------------------------------------------------------

def test_get_messages_returns_404_for_wrong_user(auth_client):
    """GET /history/{id} cuando la conversación no pertenece al usuario devuelve 404."""
    # Arrange — Supabase devuelve lista vacía (conversación no encontrada para este user)
    with patch(
        "app.api.history.get_client",
        return_value=_mock_supabase_select_single([]),
    ):
        # Act
        resp = auth_client.get("/api/v1/history/conv-other-user-uuid")

    # Assert
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 5 — POST /history/{id}/messages con role+content válidos devuelve 201
# ---------------------------------------------------------------------------

def test_add_message_returns_201(auth_client):
    """POST /history/{id}/messages con role y content válidos devuelve 201."""
    # Arrange
    conv_id = "conv-uuid-001"
    conv_row = {
        "id": conv_id,
        "user_id": FAKE_USER["user_id"],
        "project_id": "p1",
    }
    new_message = {
        "id": "msg-uuid-001",
        "conversation_id": conv_id,
        "role": "user",
        "content": "¿Cuánto cuesta la losa?",
        "created_at": "2026-04-21T10:01:00",
    }
    with patch(
        "app.api.history.get_client",
        return_value=_mock_supabase_messages_insert([conv_row], new_message),
    ):
        # Act
        resp = auth_client.post(
            f"/api/v1/history/{conv_id}/messages",
            json={"role": "user", "content": "¿Cuánto cuesta la losa?"},
        )

    # Assert
    assert resp.status_code == 201
    body = resp.json()
    assert body["conversation_id"] == conv_id
    assert body["role"] == "user"
