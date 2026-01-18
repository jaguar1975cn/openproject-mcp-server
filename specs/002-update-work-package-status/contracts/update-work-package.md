# MCP Tool Contract: update_work_package

**Feature**: 002-update-work-package-status
**Date**: 2026-01-18

## Tool Signature

```python
@app.tool()
async def update_work_package(
    work_package_id: int,
    subject: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    assignee_id: Optional[int] = None,
    estimated_hours: Optional[float] = None,
    status: Optional[Union[str, int]] = None  # NEW PARAMETER
) -> str:
```

## Input Parameters

### Existing Parameters (Unchanged)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| work_package_id | int | Yes | ID of work package to update |
| subject | str | No | New title |
| description | str | No | New description |
| start_date | str | No | Start date (YYYY-MM-DD) |
| due_date | str | No | Due date (YYYY-MM-DD) |
| assignee_id | int | No | User ID to assign |
| estimated_hours | float | No | Estimated hours |

### New Parameter

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | str \| int | No | Status name (case-insensitive) or status ID |

## Output Format

### Success Response

```json
{
  "success": true,
  "message": "Work package {id} updated successfully",
  "work_package": {
    "id": 123,
    "subject": "Task title",
    "description": "Task description",
    "start_date": "2026-01-18",
    "due_date": "2026-01-25",
    "status": "In Progress",
    "is_closed": false,
    "url": "https://openproject.example.com/work_packages/123"
  }
}
```

### Error Response - Invalid Status

```json
{
  "success": false,
  "error": "Invalid status 'InvalidName'. Available statuses: New, In Progress, Closed, Rejected"
}
```

### Error Response - Work Package Not Found

```json
{
  "success": false,
  "error": "OpenProject API error: Work package not found",
  "details": { ... }
}
```

### Error Response - No Updates Provided

```json
{
  "success": false,
  "error": "No updates provided. Specify at least one field to update."
}
```

## Example Calls

### Update Status Only (by name)

```python
update_work_package(work_package_id=123, status="In Progress")
```

### Update Status Only (by ID)

```python
update_work_package(work_package_id=123, status=2)
```

### Update Status with Other Fields

```python
update_work_package(
    work_package_id=123,
    subject="Updated Title",
    status="Closed",
    due_date="2026-02-01"
)
```

### Case-Insensitive Status Name

```python
# All equivalent:
update_work_package(work_package_id=123, status="In Progress")
update_work_package(work_package_id=123, status="in progress")
update_work_package(work_package_id=123, status="IN PROGRESS")
```

## OpenProject API Mapping

### Request Payload (PATCH /api/v3/work_packages/{id})

When status is provided, the payload includes:

```json
{
  "_links": {
    "status": {
      "href": "/api/v3/statuses/{resolved_status_id}"
    }
  }
}
```

### Response Parsing

Status information is extracted from:
- `response._links.status.title` → `status` field
- Matched against cached statuses to determine `is_closed`

## Backward Compatibility

- Calls without `status` parameter continue to work unchanged
- Empty string status is treated as "no change"
- Null/None status is treated as "no change"
