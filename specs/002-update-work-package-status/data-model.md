# Data Model: Add Status Parameter to Update Work Package

**Feature**: 002-update-work-package-status
**Date**: 2026-01-18

## Entities

### Status (Existing - Read-Only)

Represents a work package status in OpenProject. Retrieved via `get_work_package_statuses()`.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique status identifier |
| name | string | Display name (e.g., "New", "In Progress", "Closed") |
| isClosed | boolean | Whether this status represents a closed/completed state |
| isDefault | boolean | Whether this is the default status for new work packages |
| isReadonly | boolean | Whether work packages in this status are read-only |
| position | integer | Sort order for display |

**Source**: OpenProject API `/api/v3/statuses` endpoint
**Caching**: 5-minute TTL via `get_work_package_statuses(use_cache=True)`

### Work Package Update Request (Modified)

Request payload for updating a work package.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| work_package_id | integer | Yes | ID of work package to update |
| subject | string | No | New title/subject |
| description | string | No | New description |
| start_date | string (YYYY-MM-DD) | No | New start date |
| due_date | string (YYYY-MM-DD) | No | New due date |
| assignee_id | integer | No | User ID to assign |
| estimated_hours | float | No | Estimated hours |
| **status** | string \| integer | No | **NEW**: Status name or ID |

**Validation Rules**:
- `status` as string: Case-insensitive match against available status names
- `status` as integer: Direct match against status IDs
- Empty string or null: No status change (backward compatible)
- Invalid status: Return error with list of valid statuses

### Work Package Update Response (Modified)

Response payload after successful update.

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always true for successful updates |
| message | string | Human-readable success message |
| work_package.id | integer | Work package ID |
| work_package.subject | string | Current subject |
| work_package.description | string | Current description |
| work_package.start_date | string | Current start date |
| work_package.due_date | string | Current due date |
| work_package.status | string | **EXISTING**: Status name |
| **work_package.is_closed** | boolean | **NEW**: Whether status is closed |
| work_package.url | string | OpenProject web URL |

## State Transitions

### Status Update Flow

```
[User Request with status parameter]
        |
        v
[Validate work_package_id > 0]
        |
        v
[Fetch available statuses (cached)]
        |
        v
[Resolve status name/ID to status object]
        |
        ├── Invalid: Return error with available statuses
        |
        v
[Build update payload with _links.status.href]
        |
        v
[Call OpenProject PATCH API]
        |
        v
[Return response with status name and is_closed]
```

## Relationships

```
WorkPackage ──────> Status
   N          1
```

- A work package has exactly one status at any time
- A status can be assigned to many work packages
- Status transitions are unrestricted by default (OpenProject workflow configuration may impose constraints)
