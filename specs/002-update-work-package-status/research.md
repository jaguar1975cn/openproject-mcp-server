# Research: Add Status Parameter to Update Work Package

**Feature**: 002-update-work-package-status
**Date**: 2026-01-18
**Status**: Complete

## Research Tasks

### 1. OpenProject API Status Update Format

**Question**: How does the OpenProject API v3 accept status updates for work packages?

**Decision**: Use HAL+JSON `_links.status.href` format with status ID

**Rationale**: The OpenProject API v3 uses HAL+JSON format where relationships are expressed as links. Looking at the existing `create_work_package` implementation in `openproject_client.py:168-170`:

```python
"status": {
    "href": f"/api/v3/statuses/{work_package_data.status_id}"
}
```

The PATCH endpoint for work packages follows the same pattern - status is set via the `_links.status.href` field containing a reference to the status resource.

**Alternatives Considered**:
- Direct status name in payload: Not supported by OpenProject API v3
- Status ID as top-level field: Not HAL+JSON compliant

### 2. Status Resolution Strategy

**Question**: How to resolve user-provided status name/ID to the correct API format?

**Decision**: Fetch statuses via existing `get_work_package_statuses()`, then match by ID (if integer) or name (case-insensitive if string)

**Rationale**:
- The codebase already has `openproject_client.get_work_package_statuses()` which returns cached status data
- Status data includes `id`, `name`, `isClosed`, `isDefault`, `position`
- Using the existing cached endpoint avoids extra API calls (5-minute TTL cache already in place)
- Case-insensitive matching provides better UX for common status names like "in progress", "In Progress", "IN PROGRESS"

**Alternatives Considered**:
- Only accept status ID: Less user-friendly, requires users to know IDs
- API lookup on each call: Wasteful, existing caching handles this
- Fuzzy matching: Over-engineering for this use case

### 3. Error Handling for Invalid Status

**Question**: How to provide helpful error messages when status is invalid?

**Decision**: Return list of valid status names in error response

**Rationale**:
- When status validation fails, users need actionable guidance
- Listing available statuses enables self-correction on first retry
- Aligns with FR-004: "clear error message when an invalid status is provided, including a list of valid status names"

**Implementation Pattern**:
```python
if not matched_status:
    available = [s["name"] for s in statuses]
    return json.dumps({
        "success": False,
        "error": f"Invalid status '{status}'. Available statuses: {', '.join(available)}"
    })
```

### 4. Parameter Type Handling

**Question**: How to handle status parameter that can be either string (name) or int (ID)?

**Decision**: Use `Union[str, int, None]` type hint with runtime type checking

**Rationale**:
- Python's Union type allows both string and integer inputs
- Runtime `isinstance()` check determines resolution strategy
- Empty string treated as None (no status change)
- Aligns with FR-002: "support status specification by either status name (string) or status ID (integer)"

**Implementation Pattern**:
```python
from typing import Union

async def update_work_package(
    work_package_id: int,
    ...
    status: Optional[Union[str, int]] = None
) -> str:
    if status:
        if isinstance(status, int):
            # Direct ID lookup
            matched = next((s for s in statuses if s["id"] == status), None)
        else:
            # Case-insensitive name lookup
            status_lower = status.strip().lower()
            matched = next((s for s in statuses if s["name"].lower() == status_lower), None)
```

### 5. Response Format Enhancement

**Question**: What additional status information should be included in the response?

**Decision**: Include status name and is_closed flag in response

**Rationale**:
- Status name confirms the change was applied correctly
- `is_closed` flag is useful for workflow automation (detecting task completion)
- Aligns with FR-005: "include the updated status information in the successful response"
- The response already includes status name from `result.get("_links", {}).get("status", {}).get("title")`

**Enhanced Response Fields**:
```python
"work_package": {
    ...
    "status": result.get("_links", {}).get("status", {}).get("title", "Unknown"),
    "is_closed": # Need to determine from status metadata
}
```

**Note**: The `is_closed` flag requires matching the returned status to cached status data, since the PATCH response only includes the status title, not its metadata.

### 6. Backward Compatibility

**Question**: How to ensure existing calls without status parameter continue to work?

**Decision**: Make status parameter optional with default None; no status change when None or empty string

**Rationale**:
- `Optional[Union[str, int]] = None` ensures parameter is optional
- Empty string check: `if not status:` treats "" same as None
- Existing code path unchanged when status not provided
- Aligns with FR-007 and SC-005

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| API Format | HAL+JSON `_links.status.href` with status ID |
| Resolution | Case-insensitive name match or direct ID lookup |
| Caching | Use existing `get_work_package_statuses()` with 5-min TTL |
| Error Format | Return list of valid status names |
| Parameter Type | `Union[str, int, None]` with runtime type checking |
| Response | Include status name and is_closed flag |
| Backward Compat | Optional parameter, None/empty = no change |

## Implementation Notes

1. **No new dependencies required** - uses existing httpx, Pydantic, and caching
2. **Single file modification** - changes localized to `src/mcp_server.py`
3. **Test-first approach** - write tests for name resolution, ID resolution, error cases before implementation
4. **Async compliance** - status lookup is async via cached `get_work_package_statuses()`
