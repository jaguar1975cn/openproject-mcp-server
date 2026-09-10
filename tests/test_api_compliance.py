"""API compliance tests for OpenProject MCP Server."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.openproject_client import OpenProjectClient, OpenProjectAPIError
from src.models import WorkPackageCreateRequest, WorkPackageRelationCreateRequest
from pydantic import ValidationError


class TestAPICompliance:
    """Test OpenProject API compliance and integration."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenProject client."""
        client = OpenProjectClient()
        client._make_request = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_hal_json_parsing(self, mock_client):
        """Test that HAL+JSON responses are parsed correctly."""
        # Mock HAL+JSON response
        mock_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "name": "Test Project",
                        "_links": {
                            "self": {"href": "/api/v3/projects/1"}
                        }
                    }
                ]
            },
            "total": 1,
            "_links": {
                "self": {"href": "/api/v3/projects"}
            }
        }
        
        mock_client._make_request.return_value = mock_response
        
        # Test projects endpoint
        projects = await mock_client.get_projects()
        
        assert len(projects) == 1
        assert projects[0]["id"] == 1
        assert projects[0]["name"] == "Test Project"
        mock_client._make_request.assert_called_once_with("GET", "/projects")

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        """Test OpenProject-specific error response handling."""
        # Mock error response with HAL+JSON structure
        error_data = {
            "_embedded": {
                "errors": [
                    {
                        "message": "Name can't be blank",
                        "_links": {
                            "self": {"href": "/api/v3/errors/validation"}
                        }
                    }
                ]
            },
            "errors": {
                "name": ["can't be blank"]
            }
        }
        
        mock_client._make_request.side_effect = OpenProjectAPIError(
            "Validation failed", 
            status_code=422, 
            response_data=error_data
        )
        
        with pytest.raises(OpenProjectAPIError) as exc_info:
            await mock_client.get_projects()
        
        assert "Name can't be blank" in str(exc_info.value)
        assert hasattr(exc_info.value, 'detailed_errors')
        assert hasattr(exc_info.value, 'validation_errors')

    @pytest.mark.asyncio
    async def test_pagination(self, mock_client):
        """Test pagination handling for large result sets."""
        # Mock paginated responses
        page1_response = {
            "_embedded": {
                "elements": [{"id": i, "name": f"Project {i}"} for i in range(1, 101)]
            },
            "total": 150,
            "pageSize": 100,
            "offset": 0
        }
        
        page2_response = {
            "_embedded": {
                "elements": [{"id": i, "name": f"Project {i}"} for i in range(101, 151)]
            },
            "total": 150,
            "pageSize": 100,
            "offset": 100
        }
        
        mock_client._make_request.side_effect = [page1_response, page2_response]
        
        # Test paginated results
        all_projects = await mock_client.get_paginated_results("/projects")
        
        assert len(all_projects) == 150
        assert all_projects[0]["id"] == 1
        assert all_projects[-1]["id"] == 150
        assert mock_client._make_request.call_count == 2

    @pytest.mark.asyncio
    async def test_user_management(self, mock_client):
        """Test user management endpoints."""
        # Test get_users
        mock_users_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "email": "john@example.com",
                        "login": "john.doe"
                    }
                ]
            }
        }
        mock_client._make_request.return_value = mock_users_response
        
        users = await mock_client.get_users()
        assert len(users) == 1
        assert users[0]["name"] == "John Doe"
        
        # Test get_user_by_email
        user = await mock_client.get_user_by_email("john@example.com")
        assert user["email"] == "john@example.com"
        
        # Test get_user_by_id
        mock_client._make_request.return_value = users[0]
        user = await mock_client.get_user_by_id(1)
        assert user["id"] == 1

    @pytest.mark.asyncio
    async def test_caching_functionality(self, mock_client):
        """Test caching layer functionality."""
        # Mock response for cached data
        mock_types_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task"},
                    {"id": 2, "name": "Bug"}
                ]
            }
        }
        
        mock_client._fetch_work_package_types = AsyncMock(return_value=mock_types_response["_embedded"]["elements"])
        
        # First call should hit the API
        types1 = await mock_client.get_work_package_types(use_cache=True)
        assert mock_client._fetch_work_package_types.call_count == 1
        
        # Second call should use cache
        types2 = await mock_client.get_work_package_types(use_cache=True)
        assert mock_client._fetch_work_package_types.call_count == 1  # Not called again
        assert types1 == types2

    def test_validation_models(self):
        """Test Pydantic validation models."""
        # Test valid work package creation
        valid_wp = WorkPackageCreateRequest(
            subject="Test Work Package",
            project_id=1,
            start_date="2024-01-01",
            due_date="2024-01-31",
            estimated_hours=8.0
        )
        assert valid_wp.subject == "Test Work Package"
        assert valid_wp.estimated_hours == 8.0
        
        # Test invalid date format
        with pytest.raises(ValidationError) as exc_info:
            WorkPackageCreateRequest(
                subject="Test",
                project_id=1,
                start_date="01-01-2024"  # Invalid format
            )
        assert "Date must be in YYYY-MM-DD format" in str(exc_info.value)
        
        # Test due date before start date
        with pytest.raises(ValidationError) as exc_info:
            WorkPackageCreateRequest(
                subject="Test",
                project_id=1,
                start_date="2024-01-31",
                due_date="2024-01-01"  # Before start date
            )
        assert "Due date must be after start date" in str(exc_info.value)
        
        # Test negative estimated hours
        with pytest.raises(ValidationError) as exc_info:
            WorkPackageCreateRequest(
                subject="Test",
                project_id=1,
                estimated_hours=-5.0
            )
        assert "Estimated hours must be positive" in str(exc_info.value)

    def test_relation_validation(self):
        """Test work package relation validation."""
        # Test valid relation
        valid_relation = WorkPackageRelationCreateRequest(
            from_work_package_id=1,
            to_work_package_id=2,
            relation_type="follows",
            lag=2
        )
        assert valid_relation.from_work_package_id == 1
        assert valid_relation.to_work_package_id == 2
        
        # Test self-relation (invalid)
        with pytest.raises(ValidationError) as exc_info:
            WorkPackageRelationCreateRequest(
                from_work_package_id=1,
                to_work_package_id=1  # Same as from
            )
        assert "Work package cannot have a relation with itself" in str(exc_info.value)
        
        # Test invalid relation type
        with pytest.raises(ValidationError) as exc_info:
            WorkPackageRelationCreateRequest(
                from_work_package_id=1,
                to_work_package_id=2,
                relation_type="invalid_type"
            )
        assert "Invalid relation type" in str(exc_info.value)
        
        # Test negative lag
        with pytest.raises(ValidationError) as exc_info:
            WorkPackageRelationCreateRequest(
                from_work_package_id=1,
                to_work_package_id=2,
                lag=-1
            )
        assert "Lag must be zero or positive" in str(exc_info.value)


class TestGetWorkPackage:
    """Tests for get_work_package MCP tool - User Story 1 & 2."""

    @pytest.fixture
    def mock_work_package_response(self):
        """Complete mock work package response from OpenProject API."""
        return {
            "id": 42,
            "subject": "Implement user login",
            "description": {"raw": "Add authentication feature"},
            "startDate": "2026-01-15",
            "dueDate": "2026-01-30",
            "estimatedTime": "PT16H",
            "percentageDone": 50,
            "createdAt": "2026-01-10T10:00:00Z",
            "updatedAt": "2026-01-17T14:30:00Z",
            "_links": {
                "project": {
                    "href": "/api/v3/projects/5",
                    "title": "Website Redesign"
                },
                "status": {
                    "href": "/api/v3/statuses/2",
                    "title": "In Progress"
                },
                "type": {
                    "href": "/api/v3/types/1",
                    "title": "Task"
                },
                "priority": {
                    "href": "/api/v3/priorities/3",
                    "title": "High"
                },
                "assignee": {
                    "href": "/api/v3/users/1",
                    "title": "John Doe"
                },
                "responsible": {
                    "href": "/api/v3/users/2",
                    "title": "Jane Smith"
                },
                "version": {
                    "href": "/api/v3/versions/5",
                    "title": "Sprint 1"
                }
            }
        }

    # T004: Contract test for get_work_package success case
    @pytest.mark.asyncio
    async def test_get_work_package_success(self, mock_work_package_response):
        """Test get_work_package returns success with valid work package ID."""
        from src.mcp_server import get_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_by_id = AsyncMock(
                return_value=mock_work_package_response
            )

            # FastMCP wraps functions - access underlying function via .fn
            result = await get_work_package.fn(work_package_id=42)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert "work_package" in result_data
            assert result_data["work_package"]["id"] == 42
            assert result_data["work_package"]["subject"] == "Implement user login"
            mock_client.get_work_package_by_id.assert_called_once_with(42)

    # T005: Contract test for get_work_package response field mapping
    @pytest.mark.asyncio
    async def test_get_work_package_field_mapping(self, mock_work_package_response):
        """Test get_work_package maps all HAL+JSON fields correctly."""
        from src.mcp_server import get_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_by_id = AsyncMock(
                return_value=mock_work_package_response
            )

            # FastMCP wraps functions - access underlying function via .fn
            result = await get_work_package.fn(work_package_id=42)
            result_data = json.loads(result)
            wp = result_data["work_package"]

            # Direct fields
            assert wp["id"] == 42
            assert wp["subject"] == "Implement user login"
            assert wp["description"] == "Add authentication feature"
            assert wp["start_date"] == "2026-01-15"
            assert wp["due_date"] == "2026-01-30"
            assert wp["done_ratio"] == 50
            assert wp["created_at"] == "2026-01-10T10:00:00Z"
            assert wp["updated_at"] == "2026-01-17T14:30:00Z"

            # Linked fields (extracted from _links)
            assert wp["status"] == "In Progress"
            assert wp["type"] == "Task"
            assert wp["priority"] == "High"
            assert wp["assignee"] == "John Doe"
            assert wp["responsible"] == "Jane Smith"
            assert wp["project_id"] == 5
            assert wp["project_name"] == "Website Redesign"
            assert wp["version"] == "Sprint 1"

            # Estimated hours (parsed from ISO duration)
            assert wp["estimated_hours"] == 16.0

    @pytest.mark.asyncio
    async def test_get_work_package_without_version(self, mock_work_package_response):
        """Test get_work_package returns version=None when none is assigned."""
        from src.mcp_server import get_work_package

        del mock_work_package_response["_links"]["version"]

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_by_id = AsyncMock(
                return_value=mock_work_package_response
            )

            result = await get_work_package.fn(work_package_id=42)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["work_package"]["version"] is None

    # T009: Contract test for work package not found (404) error
    @pytest.mark.asyncio
    async def test_get_work_package_not_found(self):
        """Test get_work_package returns clear error when work package doesn't exist."""
        from src.mcp_server import get_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_by_id = AsyncMock(
                side_effect=OpenProjectAPIError(
                    "Work package not found",
                    status_code=404,
                    response_data={"errorIdentifier": "urn:openproject-org:api:v3:errors:NotFound"}
                )
            )

            # FastMCP wraps functions - access underlying function via .fn
            result = await get_work_package.fn(work_package_id=99999)
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "error" in result_data
            assert "not found" in result_data["error"].lower()

    # T010: Contract test for invalid ID validation error
    @pytest.mark.asyncio
    async def test_get_work_package_invalid_id(self):
        """Test get_work_package returns validation error for invalid IDs."""
        from src.mcp_server import get_work_package

        # FastMCP wraps functions - access underlying function via .fn
        # Test with zero
        result = await get_work_package.fn(work_package_id=0)
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "positive integer" in result_data["error"].lower()

        # Test with negative number
        result = await get_work_package.fn(work_package_id=-1)
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "positive integer" in result_data["error"].lower()


class TestUpdateWorkPackageStatus:
    """Tests for update_work_package status parameter - User Story 1."""

    # Sample status data for mocking
    SAMPLE_STATUSES = [
        {"id": 1, "name": "New", "isClosed": False, "isDefault": True, "position": 1},
        {"id": 2, "name": "In Progress", "isClosed": False, "isDefault": False, "position": 2},
        {"id": 3, "name": "Closed", "isClosed": True, "isDefault": False, "position": 3},
    ]

    @pytest.fixture
    def mock_update_response(self):
        """Mock response from OpenProject update work package API."""
        return {
            "id": 123,
            "subject": "Test Task",
            "description": {"raw": "Test description"},
            "startDate": "2026-01-15",
            "dueDate": "2026-01-30",
            "_links": {
                "status": {
                    "href": "/api/v3/statuses/2",
                    "title": "In Progress"
                }
            }
        }

    # T005a: Contract test for status parameter acceptance (string)
    @pytest.mark.asyncio
    async def test_update_work_package_status_by_name(self, mock_update_response):
        """Test update_work_package accepts status as string name."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_update_response)

            result = await update_work_package.fn(work_package_id=123, status="In Progress")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["work_package"]["status"] == "In Progress"
            # Verify status was included in the API call payload
            call_args = mock_client.update_work_package.call_args
            assert "_links" in call_args[0][1]
            assert "status" in call_args[0][1]["_links"]

    # T005b: Contract test for status parameter acceptance (integer ID)
    @pytest.mark.asyncio
    async def test_update_work_package_status_by_id(self, mock_update_response):
        """Test update_work_package accepts status as integer ID."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_update_response)

            result = await update_work_package.fn(work_package_id=123, status=2)
            result_data = json.loads(result)

            assert result_data["success"] is True
            # Verify status ID was used in the API call
            call_args = mock_client.update_work_package.call_args
            assert "/api/v3/statuses/2" in str(call_args)

    # T005c: Contract test for backward compatibility (no status = no change)
    @pytest.mark.asyncio
    async def test_update_work_package_without_status(self, mock_update_response):
        """Test update_work_package without status parameter (backward compatibility)."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_update_response)

            result = await update_work_package.fn(work_package_id=123, subject="New Title")
            result_data = json.loads(result)

            assert result_data["success"] is True
            # Verify status was NOT included in payload (backward compatible)
            call_args = mock_client.update_work_package.call_args
            payload = call_args[0][1]
            assert "_links" not in payload or "status" not in payload.get("_links", {})

    # T005d: Contract test for empty string status (no change)
    @pytest.mark.asyncio
    async def test_update_work_package_empty_status_ignored(self, mock_update_response):
        """Test update_work_package with empty string status is ignored."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_update_response)

            result = await update_work_package.fn(work_package_id=123, subject="New Title", status="")
            result_data = json.loads(result)

            assert result_data["success"] is True
            # Verify status was NOT included in payload
            call_args = mock_client.update_work_package.call_args
            payload = call_args[0][1]
            assert "_links" not in payload or "status" not in payload.get("_links", {})

    # T005e: Contract test for status in response
    @pytest.mark.asyncio
    async def test_update_work_package_status_in_response(self, mock_update_response):
        """Test update_work_package includes status in response."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_update_response)

            result = await update_work_package.fn(work_package_id=123, status="In Progress")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert "status" in result_data["work_package"]
            assert result_data["work_package"]["status"] == "In Progress"

    # T005f: Contract test for status combined with other fields
    @pytest.mark.asyncio
    async def test_update_work_package_status_with_other_fields(self, mock_update_response):
        """Test update_work_package with status and other fields."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_update_response)

            result = await update_work_package.fn(
                work_package_id=123,
                subject="Updated Title",
                status="In Progress",
                due_date="2026-02-15"
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            # Verify all fields were included in payload
            call_args = mock_client.update_work_package.call_args
            payload = call_args[0][1]
            assert "subject" in payload
            assert "dueDate" in payload
            assert "_links" in payload and "status" in payload["_links"]


class TestUpdateWorkPackageStatusValidation:
    """Tests for update_work_package status validation - User Story 2."""

    # Sample status data for mocking
    SAMPLE_STATUSES = [
        {"id": 1, "name": "New", "isClosed": False, "isDefault": True, "position": 1},
        {"id": 2, "name": "In Progress", "isClosed": False, "isDefault": False, "position": 2},
        {"id": 3, "name": "Closed", "isClosed": True, "isDefault": False, "position": 3},
    ]

    # T010a: Contract test for invalid status name returns error with available statuses
    @pytest.mark.asyncio
    async def test_invalid_status_name_returns_error_with_available_statuses(self):
        """Test that invalid status name returns error listing available statuses."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)

            result = await update_work_package.fn(work_package_id=123, status="InvalidStatus")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "error" in result_data
            assert "Invalid status" in result_data["error"]
            assert "InvalidStatus" in result_data["error"]
            # Should list available status names
            assert "New" in result_data["error"] or "available" in result_data["error"].lower()

    # T010b: Contract test for invalid status ID returns error with available statuses
    @pytest.mark.asyncio
    async def test_invalid_status_id_returns_error_with_available_statuses(self):
        """Test that invalid status ID returns error listing available statuses."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)

            result = await update_work_package.fn(work_package_id=123, status=999)
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "error" in result_data
            assert "Invalid status" in result_data["error"]
            assert "999" in result_data["error"]

    # T010c: Contract test for error message format matches contract
    @pytest.mark.asyncio
    async def test_error_message_format_includes_available_list(self):
        """Test that error message includes list of valid status names."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)

            result = await update_work_package.fn(work_package_id=123, status="BadStatus")
            result_data = json.loads(result)

            assert result_data["success"] is False
            error_msg = result_data["error"]
            # Error should contain available statuses list
            assert "Available statuses:" in error_msg or "available" in error_msg.lower()
            # Should contain actual status names
            assert "New" in error_msg
            assert "In Progress" in error_msg
            assert "Closed" in error_msg


class TestUpdateWorkPackageStatusResponse:
    """Tests for update_work_package response enhancement - User Story 3."""

    # Sample status data for mocking
    SAMPLE_STATUSES = [
        {"id": 1, "name": "New", "isClosed": False, "isDefault": True, "position": 1},
        {"id": 2, "name": "In Progress", "isClosed": False, "isDefault": False, "position": 2},
        {"id": 3, "name": "Closed", "isClosed": True, "isDefault": False, "position": 3},
    ]

    @pytest.fixture
    def mock_open_status_response(self):
        """Mock response with open status (In Progress)."""
        return {
            "id": 123,
            "subject": "Test Task",
            "description": {"raw": "Test description"},
            "startDate": "2026-01-15",
            "dueDate": "2026-01-30",
            "_links": {
                "status": {
                    "href": "/api/v3/statuses/2",
                    "title": "In Progress"
                }
            }
        }

    @pytest.fixture
    def mock_closed_status_response(self):
        """Mock response with closed status."""
        return {
            "id": 123,
            "subject": "Test Task",
            "description": {"raw": "Test description"},
            "startDate": "2026-01-15",
            "dueDate": "2026-01-30",
            "_links": {
                "status": {
                    "href": "/api/v3/statuses/3",
                    "title": "Closed"
                }
            }
        }

    # T014a: Contract test for response includes is_closed field
    @pytest.mark.asyncio
    async def test_response_includes_is_closed_field(self, mock_open_status_response):
        """Test that response includes is_closed field after status update."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_open_status_response)

            result = await update_work_package.fn(work_package_id=123, status="In Progress")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert "is_closed" in result_data["work_package"]

    # T014b: Contract test for is_closed=true for closed statuses
    @pytest.mark.asyncio
    async def test_is_closed_true_for_closed_status(self, mock_closed_status_response):
        """Test that is_closed=true when updating to a closed status."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_closed_status_response)

            result = await update_work_package.fn(work_package_id=123, status="Closed")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["work_package"]["is_closed"] is True

    # T014c: Contract test for is_closed=false for open statuses
    @pytest.mark.asyncio
    async def test_is_closed_false_for_open_status(self, mock_open_status_response):
        """Test that is_closed=false when updating to an open status."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_open_status_response)

            result = await update_work_package.fn(work_package_id=123, status="In Progress")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["work_package"]["is_closed"] is False


class TestWorkPackageVersion:
    """Tests for the version parameter on create_work_package / update_work_package."""

    SAMPLE_VERSIONS = [
        {"id": 5, "name": "Sprint 1", "status": "open",
         "_links": {"definingProject": {"title": "Demo"}}},
        {"id": 6, "name": "Release 2.0", "status": "open",
         "_links": {"definingProject": {"title": "Demo"}}},
    ]

    SAMPLE_STATUSES = [
        {"id": 1, "name": "New", "isClosed": False, "isDefault": True, "position": 1},
    ]

    @pytest.fixture
    def mock_wp_response(self):
        """Mock work package response carrying a version link."""
        return {
            "id": 123,
            "subject": "Test Task",
            "description": {"raw": "Test description"},
            "lockVersion": 3,
            "_links": {
                "project": {"href": "/api/v3/projects/7", "title": "Demo"},
                "status": {"href": "/api/v3/statuses/1", "title": "New"},
                "version": {"href": "/api/v3/versions/5", "title": "Sprint 1"},
            }
        }

    @pytest.mark.asyncio
    async def test_client_create_payload_includes_version_link(self):
        """Test the client maps version_id onto _links.version."""
        client = OpenProjectClient()
        client._make_request = AsyncMock(return_value={"id": 123})

        await client.create_work_package(WorkPackageCreateRequest(
            project_id=7, subject="Test Task", version_id=5
        ))

        payload = client._make_request.call_args[1]["json"]
        assert payload["_links"]["version"] == {"href": "/api/v3/versions/5"}

    @pytest.mark.asyncio
    async def test_client_create_payload_omits_version_link(self):
        """Test no version link is sent when version_id is not provided."""
        client = OpenProjectClient()
        client._make_request = AsyncMock(return_value={"id": 123})

        await client.create_work_package(WorkPackageCreateRequest(
            project_id=7, subject="Test Task"
        ))

        payload = client._make_request.call_args[1]["json"]
        assert "version" not in payload["_links"]

    @pytest.mark.asyncio
    async def test_create_work_package_version_by_name(self, mock_wp_response):
        """Test create_work_package resolves a version name within the project."""
        from src.mcp_server import create_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.create_work_package = AsyncMock(return_value=mock_wp_response)

            result = await create_work_package.fn(
                project_id=7, subject="Test Task", version="sprint 1"
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["work_package"]["version"] == "Sprint 1"
            # Version lookup must be scoped to the target project
            assert mock_client.get_versions.call_args[0][0] == 7
            wp_request = mock_client.create_work_package.call_args[0][0]
            assert wp_request.version_id == 5

    @pytest.mark.asyncio
    async def test_create_work_package_version_by_id(self, mock_wp_response):
        """Test create_work_package accepts a version ID."""
        from src.mcp_server import create_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.create_work_package = AsyncMock(return_value=mock_wp_response)

            result = await create_work_package.fn(
                project_id=7, subject="Test Task", version=6
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            wp_request = mock_client.create_work_package.call_args[0][0]
            assert wp_request.version_id == 6

    @pytest.mark.asyncio
    async def test_create_work_package_invalid_version(self):
        """Test create_work_package reports available versions for an unknown one."""
        from src.mcp_server import create_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.create_work_package = AsyncMock()

            result = await create_work_package.fn(
                project_id=7, subject="Test Task", version="Nope"
            )
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Invalid version 'Nope'" in result_data["error"]
            assert "Sprint 1" in result_data["error"]
            mock_client.create_work_package.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_work_package_without_version(self, mock_wp_response):
        """Test create_work_package stays backward compatible without version."""
        from src.mcp_server import create_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.create_work_package = AsyncMock(return_value=mock_wp_response)

            result = await create_work_package.fn(project_id=7, subject="Test Task")
            result_data = json.loads(result)

            assert result_data["success"] is True
            mock_client.get_versions.assert_not_called()
            wp_request = mock_client.create_work_package.call_args[0][0]
            assert wp_request.version_id is None

    @pytest.mark.asyncio
    async def test_update_work_package_version_by_name(self, mock_wp_response):
        """Test update_work_package resolves a version name via the WP's project."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.get_work_package_by_id = AsyncMock(return_value=mock_wp_response)
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_wp_response)

            result = await update_work_package.fn(work_package_id=123, version="Sprint 1")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["work_package"]["version"] == "Sprint 1"
            # Name lookup scoped to the work package's own project (id 7)
            assert mock_client.get_versions.call_args[0][0] == 7
            payload = mock_client.update_work_package.call_args[0][1]
            assert payload["_links"]["version"] == {"href": "/api/v3/versions/5"}
            # lockVersion carried over from the fetch used for project scoping
            assert payload["lockVersion"] == 3

    @pytest.mark.asyncio
    async def test_update_work_package_version_by_id(self, mock_wp_response):
        """Test update_work_package accepts a version ID without fetching the WP."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.get_work_package_by_id = AsyncMock(return_value=mock_wp_response)
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_wp_response)

            result = await update_work_package.fn(work_package_id=123, version=6)
            result_data = json.loads(result)

            assert result_data["success"] is True
            mock_client.get_work_package_by_id.assert_not_called()
            payload = mock_client.update_work_package.call_args[0][1]
            assert payload["_links"]["version"] == {"href": "/api/v3/versions/6"}

    @pytest.mark.asyncio
    async def test_update_work_package_invalid_version(self, mock_wp_response):
        """Test update_work_package rejects an unknown version."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.get_work_package_by_id = AsyncMock(return_value=mock_wp_response)
            mock_client.update_work_package = AsyncMock()

            result = await update_work_package.fn(work_package_id=123, version="Nope")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Invalid version 'Nope'" in result_data["error"]
            mock_client.update_work_package.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_work_package_empty_version_ignored(self, mock_wp_response):
        """Test an empty version string leaves the field untouched."""
        from src.mcp_server import update_work_package

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)
            mock_client.get_work_package_statuses = AsyncMock(return_value=self.SAMPLE_STATUSES)
            mock_client.update_work_package = AsyncMock(return_value=mock_wp_response)

            result = await update_work_package.fn(
                work_package_id=123, subject="New Title", version=""
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            payload = mock_client.update_work_package.call_args[0][1]
            assert "version" not in payload.get("_links", {})
            mock_client.get_versions.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_versions_tool(self):
        """Test the get_versions tool lists versions for a project."""
        from src.mcp_server import get_versions

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.get_versions = AsyncMock(return_value=self.SAMPLE_VERSIONS)

            result = await get_versions.fn(project_id=7)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert [v["name"] for v in result_data["versions"]] == ["Sprint 1", "Release 2.0"]
            assert result_data["versions"][0]["id"] == 5


class TestHealthCheck:
    """Tests for the health_check tool."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health_check reports a healthy connection (regression: logging TypeError)."""
        from src.mcp_server import health_check

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.test_connection = AsyncMock(return_value={
                "success": True,
                "openproject_version": "13.0.0"
            })

            result = await health_check.fn()
            result_data = json.loads(result)

            assert result_data["status"] == "healthy"
            assert result_data["openproject_connection"] == "connected"
            assert result_data["openproject_version"] == "13.0.0"
            assert "error" not in result_data

    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test health_check reports a failed OpenProject connection as degraded."""
        from src.mcp_server import health_check

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.test_connection = AsyncMock(return_value={
                "success": False,
                "message": "Connection refused"
            })

            result = await health_check.fn()
            result_data = json.loads(result)

            assert result_data["status"] == "degraded"
            assert result_data["openproject_connection"] == "failed"
            assert result_data["error"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(self):
        """Test health_check surfaces unexpected errors as unhealthy."""
        from src.mcp_server import health_check

        with patch('src.mcp_server.openproject_client') as mock_client:
            mock_client.test_connection = AsyncMock(side_effect=RuntimeError("boom"))

            result = await health_check.fn()
            result_data = json.loads(result)

            assert result_data["status"] == "unhealthy"
            assert "boom" in result_data["error"]
