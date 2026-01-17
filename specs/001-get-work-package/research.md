# Research: Get Work Package Tool

**Date**: 2026-01-17
**Feature**: 001-get-work-package

## Research Findings

### 1. OpenProject API Endpoint

**Decision**: Use `GET /api/v3/work_packages/{id}` endpoint

**Rationale**: This is the standard OpenProject v3 API endpoint for retrieving a single work package. The endpoint is already used by the existing `get_work_package_by_id` method in `openproject_client.py` (line 256-259).

**Alternatives considered**:
- Filtering via `GET /api/v3/work_packages?filters=[...]` - Rejected: Unnecessarily complex for single ID lookup

### 2. Existing Client Method

**Decision**: Reuse existing `OpenProjectClient.get_work_package_by_id()` method

**Rationale**: The method already exists and follows established patterns:
```python
async def get_work_package_by_id(self, work_package_id: int) -> Dict[str, Any]:
    """Get a specific work package by ID."""
    url = f"/work_packages/{work_package_id}"
    return await self._make_request("GET", url)
```

**Alternatives considered**:
- Creating a new method - Rejected: Would duplicate existing functionality

### 3. Response Field Mapping

**Decision**: Map HAL+JSON response to structured output matching FR-003 requirements

**Rationale**: OpenProject returns HAL+JSON format with `_links` for related resources. Must extract:
- Direct fields: `id`, `subject`, `description.raw`, `startDate`, `dueDate`, `estimatedTime`, `percentageDone`, `createdAt`, `updatedAt`
- Linked resources: `status`, `type`, `priority`, `assignee`, `responsible`, `project`

**Alternatives considered**:
- Returning raw HAL+JSON - Rejected: Too complex for AI assistant consumption
- Minimal fields only - Rejected: Does not meet SC-002 (100% field coverage)

### 4. Error Handling Strategy

**Decision**: Follow existing `OpenProjectAPIError` exception handling pattern

**Rationale**: Consistent with other tools in `mcp_server.py`. The existing client raises `OpenProjectAPIError` with status code and response data for:
- 404 Not Found → "Work package not found"
- 403 Forbidden → "Permission denied"
- 400 Bad Request → "Invalid request"

**Alternatives considered**:
- Custom exception types - Rejected: Violates simplicity principle
- Silent failure with null return - Rejected: Poor user experience

### 5. Input Validation

**Decision**: Validate work package ID is a positive integer before API call

**Rationale**: Matches pattern used in `WorkPackageRelationCreateRequest` and other request models. Prevents unnecessary API calls for obviously invalid inputs.

**Alternatives considered**:
- Defer all validation to API - Rejected: Wastes resources on invalid requests
- String ID support - Rejected: OpenProject uses integer IDs only

## Dependencies

| Dependency | Purpose | Already Present |
|------------|---------|-----------------|
| FastMCP | MCP tool decorator | ✅ Yes |
| OpenProjectClient | API client | ✅ Yes |
| OpenProjectAPIError | Error handling | ✅ Yes |
| json | Response serialization | ✅ Yes |
| utils.logging | Structured logging | ✅ Yes |

## Resolved Clarifications

No "NEEDS CLARIFICATION" items from Technical Context - all requirements are clear.
