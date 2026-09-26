"""Unit tests for sprint support and multi-version writes."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from src.models import WorkPackageCreateRequest


SAMPLE_SPRINTS = [
    {"id": 267, "name": "Update 9.0", "startDate": "2026-01-05", "finishDate": None,
     "_links": {"status": {"title": "In planning"},
                "definingWorkspace": {"title": "Demo"}}},
    {"id": 245, "name": "RELEASE 8.0", "startDate": "2025-06-01", "finishDate": "2025-07-01",
     "_links": {"status": {"title": "Completed"},
                "definingWorkspace": {"title": "Demo"}}},
]

SAMPLE_STATUSES = [{"id": 1, "name": "New", "isClosed": False}]


@pytest.fixture
def wp_response():
    """Work package response in the multi-version format with a sprint."""
    return {
        "id": 123,
        "subject": "Test Task",
        "description": {"raw": ""},
        "lockVersion": 3,
        "_links": {
            "project": {"href": "/api/v3/projects/7", "title": "Demo"},
            "status": {"href": "/api/v3/statuses/1", "title": "New"},
            "sprint": {"href": "/api/v3/sprints/267", "title": "Update 9.0"},
            "targetVersions": [{"href": "/api/v3/versions/341", "title": "Update 9.0"}],
        }
    }


@pytest.fixture
def mock_client(wp_response):
    with patch('src.mcp_server.openproject_client') as mock_client:
        mock_client.get_sprints = AsyncMock(return_value=SAMPLE_SPRINTS)
        mock_client.get_work_package_statuses = AsyncMock(return_value=SAMPLE_STATUSES)
        mock_client.get_work_package_by_id = AsyncMock(return_value=wp_response)
        mock_client.create_work_package = AsyncMock(return_value=wp_response)
        mock_client.update_work_package = AsyncMock(return_value=wp_response)
        mock_client.query_work_packages = AsyncMock(return_value=([wp_response], 1))
        yield mock_client


class TestClient:
    """Test the client's sprint and version handling."""

    @pytest.fixture
    def client(self):
        from src.openproject_client import OpenProjectClient
        client = OpenProjectClient()
        client._make_request = AsyncMock(return_value={"id": 123})
        return client

    @pytest.mark.asyncio
    async def test_create_payload_sends_version_both_ways(self, client):
        await client.create_work_package(WorkPackageCreateRequest(
            project_id=7, subject="Task", version_id=5
        ))

        links = client._make_request.call_args.kwargs["json"]["_links"]
        assert links["version"] == {"href": "/api/v3/versions/5"}
        assert links["targetVersions"] == [{"href": "/api/v3/versions/5"}]

    @pytest.mark.asyncio
    async def test_create_payload_sprint_link(self, client):
        await client.create_work_package(WorkPackageCreateRequest(
            project_id=7, subject="Task", sprint_id=267
        ))

        links = client._make_request.call_args.kwargs["json"]["_links"]
        assert links["sprint"] == {"href": "/api/v3/sprints/267"}
        assert "targetVersions" not in links

    @pytest.mark.asyncio
    async def test_get_sprints_paginates_project_endpoint(self, client):
        client._make_request.return_value = {"_embedded": {"elements": SAMPLE_SPRINTS}, "total": 2}

        sprints = await client.get_sprints(7, use_cache=False)

        assert [s["id"] for s in sprints] == [267, 245]
        assert client._make_request.call_args.args[1] == "/projects/7/sprints"
        assert client._make_request.call_args.kwargs["params"]["offset"] == 1


class TestGetSprintsTool:

    @pytest.mark.asyncio
    async def test_lists_sprints(self, mock_client):
        from src.mcp_server import get_sprints

        result = json.loads(await get_sprints.fn(project_id=7))

        assert result["success"] is True
        assert result["sprints"][1] == {
            "id": 245, "name": "RELEASE 8.0", "status": "Completed",
            "start_date": "2025-06-01", "finish_date": "2025-07-01", "project": "Demo",
        }
        mock_client.get_sprints.assert_awaited_with(7)

    @pytest.mark.asyncio
    async def test_rejects_invalid_project_id(self, mock_client):
        from src.mcp_server import get_sprints

        result = json.loads(await get_sprints.fn(project_id=0))

        assert result["success"] is False


class TestSprintInWorkPackageTools:

    @pytest.mark.asyncio
    async def test_get_work_packages_filters_by_sprint_name(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=7, sprint="update 9.0", status="all"))

        filters = mock_client.query_work_packages.call_args.kwargs["filters"]
        assert {"sprint": {"operator": "=", "values": ["267"]}} in filters
        mock_client.get_sprints.assert_awaited_with(7)
        assert result["work_packages"][0]["sprint"] == "Update 9.0"

    @pytest.mark.asyncio
    async def test_get_work_packages_invalid_sprint(self, mock_client):
        from src.mcp_server import get_work_packages

        result = json.loads(await get_work_packages.fn(project_id=7, sprint="Nope"))

        assert result["success"] is False
        assert "RELEASE 8.0" in result["error"]
        mock_client.query_work_packages.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_work_package_reports_sprint(self, mock_client):
        from src.mcp_server import get_work_package

        result = json.loads(await get_work_package.fn(work_package_id=123))

        assert result["work_package"]["sprint"] == "Update 9.0"
        assert result["work_package"]["version"] == "Update 9.0"

    @pytest.mark.asyncio
    async def test_create_resolves_sprint_in_project(self, mock_client):
        from src.mcp_server import create_work_package

        result = json.loads(await create_work_package.fn(project_id=7, subject="Task", sprint="Update 9.0"))

        assert result["success"] is True
        assert result["work_package"]["sprint"] == "Update 9.0"
        mock_client.get_sprints.assert_awaited_with(7)
        assert mock_client.create_work_package.call_args.args[0].sprint_id == 267

    @pytest.mark.asyncio
    async def test_create_invalid_sprint(self, mock_client):
        from src.mcp_server import create_work_package

        result = json.loads(await create_work_package.fn(project_id=7, subject="Task", sprint="Nope"))

        assert result["success"] is False
        assert "Invalid sprint 'Nope'" in result["error"]
        mock_client.create_work_package.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_sprint_by_name_uses_wp_project(self, mock_client):
        from src.mcp_server import update_work_package

        result = json.loads(await update_work_package.fn(work_package_id=123, sprint="release 8.0"))

        assert result["success"] is True
        mock_client.get_sprints.assert_awaited_with(7)
        payload = mock_client.update_work_package.call_args.args[1]
        assert payload["_links"]["sprint"] == {"href": "/api/v3/sprints/245"}
        assert payload["lockVersion"] == 3

    @pytest.mark.asyncio
    async def test_update_sprint_by_id_skips_fetch(self, mock_client):
        from src.mcp_server import update_work_package

        await update_work_package.fn(work_package_id=123, sprint=267)

        mock_client.get_work_package_by_id.assert_not_called()
        payload = mock_client.update_work_package.call_args.args[1]
        assert payload["_links"]["sprint"] == {"href": "/api/v3/sprints/267"}

    @pytest.mark.asyncio
    async def test_update_version_sends_target_versions(self, mock_client):
        from src.mcp_server import update_work_package
        mock_client.get_versions = AsyncMock(return_value=[{"id": 464, "name": "Update 8.0.13"}])

        await update_work_package.fn(work_package_id=123, version=464)

        links = mock_client.update_work_package.call_args.args[1]["_links"]
        assert links["targetVersions"] == [{"href": "/api/v3/versions/464"}]
        assert links["version"] == {"href": "/api/v3/versions/464"}
        assert "sprint" not in links
