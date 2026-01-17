# Data Model: Get Work Package Tool

**Date**: 2026-01-17
**Feature**: 001-get-work-package

## Entities

### WorkPackage (existing)

The `WorkPackage` model already exists in `src/models.py` (lines 17-33). No modifications needed.

```python
class WorkPackage(BaseModel):
    """Work package data model."""
    id: Optional[int] = None
    subject: str
    description: Optional[str] = ""
    project_id: int
    type_id: Optional[int] = 1
    status_id: Optional[int] = 1
    priority_id: Optional[int] = 2
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    done_ratio: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### GetWorkPackageResponse (new - output only)

Response structure returned by the `get_work_package` tool:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| success | bool | computed | Whether retrieval succeeded |
| work_package | object | API response | Work package details (below) |
| error | string | optional | Error message on failure |

### Work Package Detail Fields

| Field | Type | HAL+JSON Source | Description |
|-------|------|-----------------|-------------|
| id | int | `id` | Work package ID |
| subject | string | `subject` | Title/subject |
| description | string | `description.raw` | Raw description text |
| status | string | `_links.status.title` | Status name |
| type | string | `_links.type.title` | Type name (Task, Bug, etc.) |
| priority | string | `_links.priority.title` | Priority name |
| assignee | string/null | `_links.assignee.title` | Assigned user name |
| responsible | string/null | `_links.responsible.title` | Responsible user name |
| project_id | int | `_links.project.href` (parsed) | Project ID |
| project_name | string | `_links.project.title` | Project name |
| start_date | string/null | `startDate` | Start date (YYYY-MM-DD) |
| due_date | string/null | `dueDate` | Due date (YYYY-MM-DD) |
| estimated_hours | float/null | `estimatedTime` (parsed) | Estimated hours |
| done_ratio | int | `percentageDone` | Completion percentage (0-100) |
| created_at | string | `createdAt` | Creation timestamp (ISO 8601) |
| updated_at | string | `updatedAt` | Last update timestamp (ISO 8601) |

## Field Extraction Logic

### HAL+JSON Link Parsing

Links in OpenProject API responses follow this pattern:
```json
{
  "_links": {
    "status": {
      "href": "/api/v3/statuses/1",
      "title": "New"
    }
  }
}
```

Extract `title` for display, parse `href` for IDs when needed.

### Nullable Fields

The following fields may be null/missing in the API response:
- `assignee` - Work package may be unassigned
- `responsible` - May not have a responsible person set
- `startDate` / `dueDate` - Dates are optional
- `estimatedTime` - Time estimate is optional
- `parentId` - Top-level work packages have no parent

## Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| work_package_id (input) | Must be positive integer | "Work package ID must be a positive integer" |

## State Transitions

N/A - This is a read-only operation. No state changes occur.
