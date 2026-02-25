"""Tests for authentication logic in auth.py.

Pure crypto functions (hash/verify password, JWT) require no mocking.
Functions that touch the database (create_user, authenticate_user,
get_user_from_token) use unittest.mock to inject a fake connection.
"""
import pytest
from unittest.mock import patch, MagicMock

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_differs_from_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_bcrypt_produces_unique_salts(self):
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert h1 != h2  # each call uses a different random salt


# ---------------------------------------------------------------------------
# JWT token creation and verification
# ---------------------------------------------------------------------------

class TestJWT:
    def test_create_token_returns_string(self):
        token = create_access_token({"user_id": 1, "email": "test@example.com"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token_returns_payload(self):
        payload_in = {"user_id": 42, "email": "alice@example.com"}
        token = create_access_token(payload_in)
        payload_out = verify_token(token)
        assert payload_out is not None
        assert payload_out["user_id"] == 42
        assert payload_out["email"] == "alice@example.com"

    def test_verify_garbage_token_returns_none(self):
        assert verify_token("not.a.valid.token") is None

    def test_verify_tampered_token_returns_none(self):
        token = create_access_token({"user_id": 1})
        # Corrupt the last 4 characters of the signature
        tampered = token[:-4] + "XXXX"
        assert verify_token(tampered) is None

    def test_verify_empty_string_returns_none(self):
        assert verify_token("") is None


# ---------------------------------------------------------------------------
# create_user (DB-dependent)
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_db_connection_failure(self):
        from auth import create_user
        with patch("auth.get_db_connection", return_value=None):
            result = create_user("Alice", "alice@example.com", "password123")
        assert result["success"] is False
        assert "Database connection failed" in result["message"]

    def test_duplicate_email_rejected(self):
        from auth import create_user
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate existing user found
        mock_cursor.fetchone.return_value = {"id": 1}

        with patch("auth.get_db_connection", return_value=mock_conn):
            result = create_user("Bob", "existing@example.com", "pass123")

        assert result["success"] is False
        assert "already registered" in result["message"]

    def test_successful_creation_returns_token_and_user(self):
        from auth import create_user
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None   # no duplicate
        mock_cursor.lastrowid = 99

        with patch("auth.get_db_connection", return_value=mock_conn):
            result = create_user("Carol", "carol@example.com", "pass123")

        assert result["success"] is True
        assert result["user"]["email"] == "carol@example.com"
        assert result["user"]["id"] == 99
        assert "token" in result
        assert isinstance(result["token"], str)


# ---------------------------------------------------------------------------
# authenticate_user (DB-dependent)
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_db_connection_failure(self):
        from auth import authenticate_user
        with patch("auth.get_db_connection", return_value=None):
            result = authenticate_user("user@example.com", "pass")
        assert result["success"] is False

    def test_user_not_found(self):
        from auth import authenticate_user
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("auth.get_db_connection", return_value=mock_conn):
            result = authenticate_user("noone@example.com", "pass")

        assert result["success"] is False
        assert "Invalid email or password" in result["message"]

    def test_wrong_password(self):
        from auth import authenticate_user
        hashed = hash_password("correct_pass")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": 1, "name": "Dave", "email": "dave@example.com",
            "password_hash": hashed, "is_active": True,
        }

        with patch("auth.get_db_connection", return_value=mock_conn):
            result = authenticate_user("dave@example.com", "wrong_pass")

        assert result["success"] is False

    def test_inactive_account_rejected(self):
        from auth import authenticate_user
        hashed = hash_password("pass123")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": 2, "name": "Eve", "email": "eve@example.com",
            "password_hash": hashed, "is_active": False,
        }

        with patch("auth.get_db_connection", return_value=mock_conn):
            result = authenticate_user("eve@example.com", "pass123")

        assert result["success"] is False
        assert "disabled" in result["message"]

    def test_successful_login_returns_token_and_user(self):
        from auth import authenticate_user
        hashed = hash_password("correct_pass")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": 5, "name": "Frank", "email": "frank@example.com",
            "password_hash": hashed, "is_active": True,
        }

        with patch("auth.get_db_connection", return_value=mock_conn):
            result = authenticate_user("frank@example.com", "correct_pass")

        assert result["success"] is True
        assert result["user"]["email"] == "frank@example.com"
        assert "token" in result
