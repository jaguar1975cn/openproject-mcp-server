"""Unit tests for get_work_packages filtering and pagination."""
import json
import pytest
from unittest.mock import AsyncMock, patch


SAMPLE_STATUSES = [
    {"id": 1, "name": "New", "isClosed": False},
    {"id": 7, "name": "In Progress", "isClosed": False},
]

SAMPLE_VERSIONS = [
    {"id": 3, "name": "Release 1.0"},
    {"id": 4, "name": "Release 2.0"},
]


def _wp(wp_id, version=None):
    links = {"status": {"title": "New"}}
    if version:
        links["version"] = {"title": version}
    return {"id": wp_id, "subject": f"WP {wp_id}", "_links": links}


def _page(elements, total):
    return {"_embedded": {"elements": elements}, "total": total}


class TestCollectPages:
    """Test OpenProjectClient._collect_pages pagination."""

    @pytest.fixture
    def client(self):
        from src.openproject_client import OpenProjectClient
        client = OpenProjectClient()
        client._make_request = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_offset_is_page_number(self, client):
        client._make_request.side_effect = [
            _page([_wp(i) for i in range(100)], 150),
            _page([_wp(i) for i in range(100, 150)], 150),
        ]

        results, total = await client._collect_pages("/projects/1/work_packages")

        assert len(results) == 150
        assert total == 150
        offsets = [c.kwargs["params"]["offset"] for c in client._make_request.call_args_list]
        assert offsets == [1, 2]

    @pytest.mark.asyncio
    async def test_max_results_stops_early(self, client):
        client._make_request.side_effect = [
            _page([_wp(i) for i in range(100)], 500),
            _page([_wp(i) for i in range(100, 200)], 500),
        ]

        results, total = await client._collect_pages("/x", max_results=150)

        assert len(results) == 150
        assert total == 500
        assert client._make_request.call_count == 2

    @pytest.mark.asyncio
    async def test_small_max_results_shrinks_page_size(self, client):
        client._make_request.return_value = _page([_wp(i) for i in range(10)], 40)

        results, _ = await client._collect_pages("/x", max_results=10)

        assert len(results) == 10
        assert client._make_request.call_args.kwargs["params"]["pageSize"] == 10
        assert client._make_request.call_count == 1

    @pytest.mark.asyncio
    async def test_query_work_packages_sends_filters_as_json(self, client):
        client._make_request.return_value = _page([_wp(1)], 1)
        filters = [{"version": {"operator": "=", "values": ["3"]}}]

        await client.query_work_packages(1, filters=filters)

        params = client._make_request.call_args.kwargs["params"]
        assert json.loads(params["filters"]) == filters


class TestGetWorkPackagesTool:
    """Test the get_work_packages MCP tool."""

    @pytest.fixture
    def mock_client(self):
        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=SAMPLE_STATUSES)
            mock_client.get_versions = AsyncMock(return_value=SAMPLE_VERSIONS)
            mock_client.query_work_packages = AsyncMock(
                return_value=([_wp(1, "Release 1.0")], 1)
            )
            yield mock_client

    def _filters(self, mock_client):
        return mock_client.query_work_packages.call_args.kwargs["filters"]

    @pytest.mark.asyncio
    async def test_defaults_to_open_and_100(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5))

        assert result["success"] is True
        assert self._filters(mock_client) == [{"status": {"operator": "o", "values": []}}]
        assert mock_client.query_work_packages.call_args.kwargs["max_results"] == 100
        assert result["work_packages"][0]["version"] == "Release 1.0"

    @pytest.mark.asyncio
    async def test_filter_by_version_name(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, version="release 2.0", status="all")

        assert self._filters(mock_client) == [
            {"status": {"operator": "*", "values": []}},
            {"version": {"operator": "=", "values": ["4"]}},
        ]
        mock_client.get_versions.assert_awaited_with(5)

    @pytest.mark.asyncio
    async def test_filter_by_version_id(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, version=3)

        assert {"version": {"operator": "=", "values": ["3"]}} in self._filters(mock_client)

    @pytest.mark.asyncio
    async def test_invalid_version(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5, version="Nope"))

        assert result["success"] is False
        assert "Release 1.0" in result["error"]
        mock_client.query_work_packages.assert_not_called()

    @pytest.mark.asyncio
    async def test_closed_status(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, status="Closed")

        assert self._filters(mock_client) == [{"status": {"operator": "c", "values": []}}]

    @pytest.mark.asyncio
    async def test_specific_status_name(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, status="in progress")

        assert self._filters(mock_client) == [{"status": {"operator": "=", "values": ["7"]}}]

    @pytest.mark.asyncio
    async def test_invalid_status(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5, status="Bogus"))

        assert result["success"] is False
        mock_client.query_work_packages.assert_not_called()

    @pytest.mark.asyncio
    async def test_reports_truncation(self, mock_client):
        from src.mcp_server import get_work_packages
        mock_client.query_work_packages.return_value = ([_wp(1), _wp(2)], 250)

        result = json.loads(await get_work_packages.fn(project_id=5, max_results=2))

        assert result["total"] == 250
        assert result["returned"] == 2
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_unlimited_max_results(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5, max_results=None))

        assert result["truncated"] is False
        assert mock_client.query_work_packages.call_args.kwargs["max_results"] is None

    @pytest.mark.asyncio
    async def test_rejects_non_positive_max_results(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5, max_results=0))

        assert result["success"] is False
        mock_client.query_work_packages.assert_not_called()


class TestVersionTitle:
    """Test _version_title across single- and multi-version responses."""

    def test_single_version_link(self):
        from src.mcp_server import _version_title
        assert _version_title({"_links": {"version": {"title": "Release 1.0"}}}) == "Release 1.0"

    def test_target_versions_list(self):
        from src.mcp_server import _version_title
        wp = {"_links": {"targetVersions": [
            {"href": "/api/v3/versions/3", "title": "Release 1.0"},
            {"href": "/api/v3/versions/4", "title": "Release 2.0"},
        ]}}
        assert _version_title(wp) == "Release 1.0, Release 2.0"

    def test_no_version(self):
        from src.mcp_server import _version_title
        assert _version_title({"_links": {"version": None, "targetVersions": []}}) is None


class TestExcludeStatus:
    """Test the exclude_status parameter of get_work_packages."""

    STATUSES = SAMPLE_STATUSES + [
        {"id": 3, "name": "Closed", "isClosed": True},
        {"id": 4, "name": "Rejected", "isClosed": True},
    ]

    @pytest.fixture
    def mock_client(self):
        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.STATUSES)
            mock_client.query_work_packages = AsyncMock(return_value=([], 0))
            yield mock_client

    def _filters(self, mock_client):
        return mock_client.query_work_packages.call_args.kwargs["filters"]

    @pytest.mark.asyncio
    async def test_open_minus_status_becomes_single_equals_filter(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, exclude_status="in progress")

        assert self._filters(mock_client) == [{"status": {"operator": "=", "values": ["1"]}}]

    @pytest.mark.asyncio
    async def test_closed_minus_status(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, status="closed", exclude_status="Rejected")

        assert self._filters(mock_client) == [{"status": {"operator": "=", "values": ["3"]}}]

    @pytest.mark.asyncio
    async def test_all_minus_list_of_names_and_ids(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, status="all", exclude_status=["Rejected", 3])

        assert self._filters(mock_client) == [{"status": {"operator": "!", "values": ["3", "4"]}}]

    @pytest.mark.asyncio
    async def test_everything_excluded_returns_empty_without_query(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5, status="New", exclude_status="New"))

        assert result["success"] is True
        assert result["total"] == 0
        mock_client.query_work_packages.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_exclude_status(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=5, exclude_status=["New", "Bogus"]))

        assert result["success"] is False
        assert "Bogus" in result["error"]
        mock_client.query_work_packages.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_list_adds_no_filter(self, mock_client):
        from src.mcp_server import get_work_packages

        await get_work_packages.fn(project_id=5, exclude_status=[])

        assert self._filters(mock_client) == [{"status": {"operator": "o", "values": []}}]
