# Quickstart: Add Status Parameter to Update Work Package

**Feature**: 002-update-work-package-status
**Date**: 2026-01-18

## Overview

This feature adds a `status` parameter to the existing `update_work_package` MCP tool, allowing users to change work package status (e.g., "New" → "In Progress" → "Closed") without leaving the AI assistant interface.

## Prerequisites

- OpenProject MCP Server running (local or Docker)
- Valid OpenProject API key configured
- At least one work package in your OpenProject instance

## Usage Examples

### 1. Update Status by Name

```
Update work package 123 status to "In Progress"
```

The MCP tool call:
```python
update_work_package(work_package_id=123, status="In Progress")
```

Response:
```json
{
  "success": true,
  "message": "Work package 123 updated successfully",
  "work_package": {
    "id": 123,
    "subject": "My Task",
    "status": "In Progress",
    "is_closed": false,
    "url": "https://openproject.example.com/work_packages/123"
  }
}
```

### 2. Close a Task

```
Mark work package 456 as closed
```

The MCP tool call:
```python
update_work_package(work_package_id=456, status="Closed")
```

Response includes `is_closed: true` to confirm the task is now in a completed state.

### 3. Update Multiple Fields Including Status

```
Update work package 789 with new title "Final Review" and status "In Progress"
```

The MCP tool call:
```python
update_work_package(
    work_package_id=789,
    subject="Final Review",
    status="In Progress"
)
```

### 4. Find Available Statuses

If you're unsure what statuses are available:

```python
get_work_package_statuses()
```

Returns a list of all configured statuses in your OpenProject instance.

## Error Handling

### Invalid Status Name

If you provide a status that doesn't exist:

```python
update_work_package(work_package_id=123, status="InvalidStatus")
```

Response:
```json
{
  "success": false,
  "error": "Invalid status 'InvalidStatus'. Available statuses: New, In Progress, Closed, Rejected"
}
```

### Case-Insensitive Matching

Status names are matched case-insensitively. These are all equivalent:
- `status="In Progress"`
- `status="in progress"`
- `status="IN PROGRESS"`

### Using Status ID

If you know the status ID (from `get_work_package_statuses()`), you can use it directly:

```python
update_work_package(work_package_id=123, status=2)  # ID instead of name
```

## Testing the Feature

### Quick Validation

1. Get a list of work packages:
   ```python
   get_work_packages(project_id=1)
   ```

2. Pick a work package ID and check current status

3. Update the status:
   ```python
   update_work_package(work_package_id=<id>, status="In Progress")
   ```

4. Verify the response shows the new status

### Full Test Cycle

1. Create a work package (starts with default status, usually "New")
2. Update to "In Progress"
3. Update to "Closed"
4. Verify `is_closed: true` in the response

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid status" error | Use `get_work_package_statuses()` to see available options |
| Status not changing | Check if work package is in a read-only status |
| API error | Verify OpenProject connection with `health_check()` |

## Related Tools

- `get_work_package_statuses()` - List all available statuses
- `get_work_package(work_package_id)` - Get current work package details
- `create_work_package(...)` - Create new work packages (uses status_id)
