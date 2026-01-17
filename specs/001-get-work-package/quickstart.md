# Quickstart: Get Work Package Tool

**Feature**: 001-get-work-package
**Date**: 2026-01-17

## Overview

The `get_work_package` tool retrieves complete details of a specific work package from OpenProject by its ID.

## Prerequisites

1. OpenProject MCP Server running (local or Docker)
2. Valid OpenProject API key configured
3. Access to at least one project with work packages

## Usage

### Basic Usage

Request a work package by ID:

```
Get the details of work package 42
```

The AI assistant will call `get_work_package(work_package_id=42)` and return:

```json
{
  "success": true,
  "work_package": {
    "id": 42,
    "subject": "Implement user login",
    "description": "Add authentication feature",
    "status": "In Progress",
    "type": "Task",
    "priority": "High",
    "assignee": "John Doe",
    "project_name": "Website Redesign",
    "start_date": "2026-01-15",
    "due_date": "2026-01-30",
    "done_ratio": 50
  }
}
```

### Error Handling

**Work package not found:**
```
Get work package 99999
```
Returns:
```json
{
  "success": false,
  "error": "Work package with ID 99999 not found"
}
```

**Invalid ID:**
```
Get work package -5
```
Returns:
```json
{
  "success": false,
  "error": "Work package ID must be a positive integer"
}
```

## Chaining with Other Tools

The `get_work_package` tool works seamlessly with other MCP tools:

### 1. Get then Update

```
First get the details of work package 42, then update its due date to 2026-02-15
```

### 2. Get then Create Dependency

```
Get work package 42 and create a dependency so that work package 43 follows it
```

### 3. Inspect Before Assignment

```
Show me work package 42, then assign it to john@example.com
```

## Response Fields

| Field | Description |
|-------|-------------|
| id | Unique work package identifier |
| subject | Title/name of the work package |
| description | Detailed description text |
| status | Current status (New, In Progress, Closed, etc.) |
| type | Work package type (Task, Bug, Feature, etc.) |
| priority | Priority level (Low, Normal, High, etc.) |
| assignee | User assigned to complete the work |
| responsible | User accountable for the work |
| project_name | Name of the parent project |
| start_date | Planned start date (YYYY-MM-DD) |
| due_date | Planned due date (YYYY-MM-DD) |
| estimated_hours | Estimated time to complete |
| done_ratio | Completion percentage (0-100) |
| created_at | When the work package was created |
| updated_at | When last modified |

## Verification

To verify the feature works correctly:

1. Create a test work package using `create_work_package`
2. Note the returned ID
3. Call `get_work_package` with that ID
4. Verify all fields match the creation input
