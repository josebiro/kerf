import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.auth import get_optional_user, require_user


class TestGetOptionalUser:
    @pytest.mark.asyncio
    async def test_returns_none_without_header(self):
        user = await get_optional_user(authorization=None)
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_with_empty_header(self):
        user = await get_optional_user(authorization="")
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_user_with_valid_token(self):
        mock_response = MagicMock()
        mock_response.user = MagicMock()
        mock_response.user.id = "user-123"
        mock_response.user.email = "test@example.com"

        with patch("app.auth._get_supabase_client") as mock_client:
            mock_client.return_value.auth.get_user = MagicMock(return_value=mock_response)
            user = await get_optional_user(authorization="Bearer fake-jwt-token")
            assert user is not None
            assert user["id"] == "user-123"
            assert user["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_with_invalid_token(self):
        with patch("app.auth._get_supabase_client") as mock_client:
            mock_client.return_value.auth.get_user = MagicMock(side_effect=Exception("Invalid token"))
            user = await get_optional_user(authorization="Bearer bad-token")
            assert user is None


class TestRequireUser:
    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self):
        user = {"id": "user-123", "email": "test@example.com"}
        result = await require_user(user=user)
        assert result == user

    @pytest.mark.asyncio
    async def test_raises_401_when_no_user(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_user(user=None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail
