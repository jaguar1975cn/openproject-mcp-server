"""Unit tests for status resolution helper function."""
import pytest
from unittest.mock import AsyncMock, patch


# Sample status data matching OpenProject API response format
SAMPLE_STATUSES = [
    {"id": 1, "name": "New", "isClosed": False, "isDefault": True, "position": 1},
    {"id": 2, "name": "In Progress", "isClosed": False, "isDefault": False, "position": 2},
    {"id": 3, "name": "Closed", "isClosed": True, "isDefault": False, "position": 3},
    {"id": 4, "name": "Rejected", "isClosed": True, "isDefault": False, "position": 4},
]


class TestStatusResolution:
    """Test _resolve_status helper function."""

    @pytest.fixture
    def mock_statuses(self):
        """Mock get_work_package_statuses to return sample data."""
        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=SAMPLE_STATUSES)
            yield mock_client

    @pytest.mark.asyncio
    async def test_resolve_status_by_name_exact_case(self, mock_statuses):
        """Test status resolution by exact name match."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("In Progress")

        assert result is not None
        assert result["id"] == 2
        assert result["name"] == "In Progress"
        assert result["isClosed"] is False

    @pytest.mark.asyncio
    async def test_resolve_status_by_name_case_insensitive_lower(self, mock_statuses):
        """Test status resolution with lowercase name."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("in progress")

        assert result is not None
        assert result["id"] == 2
        assert result["name"] == "In Progress"

    @pytest.mark.asyncio
    async def test_resolve_status_by_name_case_insensitive_upper(self, mock_statuses):
        """Test status resolution with uppercase name."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("IN PROGRESS")

        assert result is not None
        assert result["id"] == 2
        assert result["name"] == "In Progress"

    @pytest.mark.asyncio
    async def test_resolve_status_by_name_with_whitespace(self, mock_statuses):
        """Test status resolution with leading/trailing whitespace."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("  In Progress  ")

        assert result is not None
        assert result["id"] == 2

    @pytest.mark.asyncio
    async def test_resolve_status_by_id_integer(self, mock_statuses):
        """Test status resolution by integer ID."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status(3)

        assert result is not None
        assert result["id"] == 3
        assert result["name"] == "Closed"
        assert result["isClosed"] is True

    @pytest.mark.asyncio
    async def test_resolve_status_by_id_first_status(self, mock_statuses):
        """Test status resolution by ID for first status."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status(1)

        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "New"

    @pytest.mark.asyncio
    async def test_resolve_status_none_returns_none(self, mock_statuses):
        """Test that None input returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_status_empty_string_returns_none(self, mock_statuses):
        """Test that empty string returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_status_whitespace_only_returns_none(self, mock_statuses):
        """Test that whitespace-only string returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("   ")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_status_invalid_name_returns_none(self, mock_statuses):
        """Test that invalid status name returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status("InvalidStatusName")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_status_invalid_id_returns_none(self, mock_statuses):
        """Test that invalid status ID returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_status_negative_id_returns_none(self, mock_statuses):
        """Test that negative ID returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status(-1)

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_status_zero_id_returns_none(self, mock_statuses):
        """Test that zero ID returns None."""
        from src.mcp_server import _resolve_status

        result = await _resolve_status(0)

        assert result is None
