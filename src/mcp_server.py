"""FastMCP server for OpenProject integration."""
import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from fastmcp import FastMCP
from openproject_client import OpenProjectClient, OpenProjectAPIError
from models import ProjectCreateRequest, WorkPackageCreateRequest, WorkPackageRelationCreateRequest
from pydantic import ValidationError
from config import settings
from handlers.resources import ResourceHandler
from utils.logging import get_logger, log_tool_execution, log_error

logger = get_logger(__name__)


# Initialize FastMCP server with minimal output
import os
os.environ['FASTMCP_QUIET'] = '1'  # Try to suppress FastMCP banner
app = FastMCP("OpenProject MCP Server")

# Initialize OpenProject client and resource handler
openproject_client = OpenProjectClient()
resource_handler = ResourceHandler(openproject_client)


# Helper function for status resolution
def _match_named(
    items: List[Dict[str, Any]],
    value: Optional[Union[str, int]]
) -> Optional[Dict[str, Any]]:
    """Find an entry in a list of OpenProject resources by ID or name.

    Args:
        items: Resources to search, each with "id" and "name" keys.
        value: Resource name (string, case-insensitive) or ID (integer).
               None or an empty/whitespace-only string returns None.

    Returns:
        The matching resource dict, or None if not found/invalid.
    """
    if value is None:
        return None

    if isinstance(value, int):
        # Direct ID lookup - must be positive
        if value <= 0:
            return None
        return next((i for i in items if i.get("id") == value), None)

    # Case-insensitive name lookup
    name = value.strip().lower()
    if not name:
        return None
    return next((i for i in items if i.get("name", "").lower() == name), None)


def _available_names(items: List[Dict[str, Any]]) -> str:
    """Format resource names for an error message."""
    return ", ".join(str(i.get("name")) for i in items) or "none"


async def _resolve_status(status: Optional[Union[str, int]]) -> Optional[Dict[str, Any]]:
    """Resolve a status name or ID to a status dict.

    Args:
        status: Status name (string, case-insensitive) or status ID (integer).
                None or empty string returns None.

    Returns:
        Status dict with id, name, isClosed, etc. or None if not found/invalid.
    """
    if status is None:
        return None

    # Fetch available statuses (uses cached data with 5-min TTL)
    return _match_named(await openproject_client.get_work_package_statuses(), status)


async def _resolve_type(
    type_: Optional[Union[str, int]],
    project_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Resolve a work package type name or ID to a type dict.

    Args:
        type_: Type name (string, case-insensitive) or type ID (integer).
               None or empty string returns None.
        project_id: Restrict the lookup to the types enabled for this project.

    Returns:
        Type dict with id, name, etc. or None if not found/invalid.
    """
    if type_ is None:
        return None

    return _match_named(await openproject_client.get_work_package_types(project_id), type_)


async def _resolve_priority(priority: Optional[Union[str, int]]) -> Optional[Dict[str, Any]]:
    """Resolve a priority name or ID to a priority dict.

    Args:
        priority: Priority name (string, case-insensitive) or priority ID (integer).
                  None or empty string returns None.

    Returns:
        Priority dict with id, name, etc. or None if not found/invalid.
    """
    if priority is None:
        return None

    return _match_named(await openproject_client.get_priorities(), priority)


async def _resolve_version(
    version: Optional[Union[str, int]],
    project_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Resolve a version name or ID to a version dict.

    Args:
        version: Version name (string, case-insensitive) or version ID (integer).
                 None or empty string returns None.
        project_id: Restrict the lookup to this project's versions. Recommended for
                    name lookups, since version names are only unique per project.

    Returns:
        Version dict with id, name, etc. or None if not found/invalid.
    """
    if version is None:
        return None

    # Fetch available versions (uses cached data with 5-min TTL)
    return _match_named(await openproject_client.get_versions(project_id), version)


async def _resolve_sprint(
    sprint: Optional[Union[str, int]],
    project_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Resolve a sprint name or ID to a sprint dict.

    Args:
        sprint: Sprint name (string, case-insensitive) or sprint ID (integer).
                None or empty string returns None.
        project_id: Restrict the lookup to the sprints available to this project.

    Returns:
        Sprint dict with id, name, etc. or None if not found/invalid.
    """
    if sprint is None:
        return None

    # Fetch available sprints (uses cached data with 5-min TTL)
    return _match_named(await openproject_client.get_sprints(project_id), sprint)


def _sprint_title(work_package: Dict[str, Any]) -> Optional[str]:
    """Extract the sprint name from a work package API response."""
    return (work_package.get("_links", {}).get("sprint") or {}).get("title")


def _version_title(work_package: Dict[str, Any]) -> Optional[str]:
    """Extract the version name from a work package API response.

    Instances that allow several versions per work package return a
    `targetVersions` list instead of a single `version` link; their titles
    are joined with ", ".
    """
    links = work_package.get("_links", {})
    title = (links.get("version") or {}).get("title")
    if title:
        return title
    titles = [v.get("title") for v in links.get("targetVersions") or [] if v.get("title")]
    return ", ".join(titles) or None


# Add health check tool for MCP
@app.tool()
async def health_check() -> str:
    """Health check tool to verify OpenProject MCP Server is running and connected.
    
    Returns:
        JSON string with server and OpenProject connection status
    """
    try:
        # Test OpenProject connection
        connection_result = await openproject_client.test_connection()
        
        if connection_result.get('success'):
            result = {
                "status": "healthy",
                "message": "OpenProject MCP Server is currently running",
                "openproject_connection": "connected",
                "openproject_version": connection_result.get('openproject_version', 'unknown'),
                "openproject_url": settings.openproject_url
            }
        else:
            result = {
                "status": "degraded", 
                "message": "OpenProject MCP Server is running but OpenProject connection failed",
                "openproject_connection": "failed",
                "error": connection_result.get('message', 'Unknown connection error'),
                "openproject_url": settings.openproject_url
            }
        
        log_tool_execution(
            logger,
            "health_check",
            connection_result.get('success', False),
            status=result["status"]
        )
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "unhealthy",
            "message": "OpenProject MCP Server encountered an error",
            "error": str(e)
        }
        log_error(logger, e, {"tool": "health_check"})
        return json.dumps(error_result, indent=2)


@app.tool()
async def create_project(name: str, description: str = "") -> str:
    """Create a new project in OpenProject.
    
    Args:
        name: Project name (required)
        description: Project description (optional)
    
    Returns:
        JSON string with project creation result
    """
    try:
        # Validate input
        if not name or not name.strip():
            return json.dumps({
                "success": False,
                "error": "Project name is required and cannot be empty"
            })
        
        # Create project request
        project_request = ProjectCreateRequest(
            name=name.strip(),
            description=description.strip() if description else ""
        )
        
        # Call OpenProject API
        result = await openproject_client.create_project(project_request)
        
        return json.dumps({
            "success": True,
            "message": f"Project '{name}' created successfully",
            "project": {
                "id": result.get("id"),
                "name": result.get("name"),
                "description": result.get("description", {}).get("raw", ""),
                "status": result.get("status"),
                "url": f"{settings.openproject_url}/projects/{result.get('identifier', result.get('id'))}"
            }
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def create_work_package(
    project_id: int,
    subject: str,
    description: str = "",
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    parent_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    estimated_hours: Optional[float] = None,
    version: Optional[Union[str, int]] = None,
    type: Optional[Union[str, int]] = None,
    priority: Optional[Union[str, int]] = None,
    status: Optional[Union[str, int]] = None,
    sprint: Optional[Union[str, int]] = None
) -> str:
    """Create a work package in a project with dates for Gantt chart.
    
    Args:
        project_id: ID of the project to create work package in
        subject: Work package title/subject
        description: Detailed description (optional)
        start_date: Start date in YYYY-MM-DD format (optional)
        due_date: Due date in YYYY-MM-DD format (optional)
        parent_id: Parent work package ID for hierarchy (optional)
        assignee_id: User ID to assign work package to (optional)
        estimated_hours: Estimated hours for completion (optional)
        version: Version/milestone name (string, case-insensitive) or version ID
                 (integer) to assign the work package to (optional)
        type: Type name (e.g. "Task", "Bug", "Milestone") or type ID (optional,
              defaults to the instance default type)
        priority: Priority name (e.g. "High") or priority ID (optional, defaults
                  to Normal)
        status: Initial status name (e.g. "New") or status ID (optional, defaults
                to the default status; OpenProject workflow rules may reject a
                status that is not a valid starting point)
        sprint: Sprint name (string, case-insensitive) or sprint ID (integer) to
                plan the work package into (optional). Sprints are separate from
                versions; setting one does not set the other.
    
    Returns:
        JSON string with work package creation result
    """
    try:
        # Validate input
        if not subject or not subject.strip():
            return json.dumps({
                "success": False,
                "error": "Work package subject is required and cannot be empty"
            })
        
        if project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })
        
        # Validate date format if provided
        if start_date and not _is_valid_date_format(start_date):
            return json.dumps({
                "success": False,
                "error": "Start date must be in YYYY-MM-DD format"
            })
        
        if due_date and not _is_valid_date_format(due_date):
            return json.dumps({
                "success": False,
                "error": "Due date must be in YYYY-MM-DD format"
            })
        
        # Resolve the named fields to IDs. Types, versions and sprints are
        # per-project; statuses and priorities are instance-wide.
        resolved_ids = {}
        for field, value, resolve, fetch_available, scoped in (
            ("type", type,
             lambda v: _resolve_type(v, project_id),
             lambda: openproject_client.get_work_package_types(project_id), True),
            ("version", version,
             lambda v: _resolve_version(v, project_id),
             lambda: openproject_client.get_versions(project_id), True),
            ("sprint", sprint,
             lambda v: _resolve_sprint(v, project_id),
             lambda: openproject_client.get_sprints(project_id), True),
            ("status", status, _resolve_status,
             openproject_client.get_work_package_statuses, False),
            ("priority", priority, _resolve_priority,
             openproject_client.get_priorities, False),
        ):
            if value is None or value == "":
                continue
            
            resolved = await resolve(value)
            if not resolved:
                scope = f" for project {project_id}" if scoped else ""
                return json.dumps({
                    "success": False,
                    "error": f"Invalid {field} '{value}'{scope}. "
                             f"Available {field}s: {_available_names(await fetch_available())}"
                })
            resolved_ids[field] = resolved["id"]
        
        # Only override the model defaults for fields that were provided
        optional_ids = {
            f"{field}_id": resolved_ids[field]
            for field in ("type", "status", "priority")
            if field in resolved_ids
        }
        
        # Create work package request
        wp_request = WorkPackageCreateRequest(
            project_id=project_id,
            subject=subject.strip(),
            description=description.strip() if description else "",
            start_date=start_date,
            due_date=due_date,
            parent_id=parent_id,
            assignee_id=assignee_id,
            estimated_hours=estimated_hours,
            version_id=resolved_ids.get("version"),
            sprint_id=resolved_ids.get("sprint"),
            **optional_ids
        )
        
        # Call OpenProject API
        result = await openproject_client.create_work_package(wp_request)
        
        return json.dumps({
            "success": True,
            "message": f"Work package '{subject}' created successfully",
            "work_package": {
                "id": result.get("id"),
                "subject": result.get("subject"),
                "description": result.get("description", {}).get("raw", ""),
                "project_id": project_id,
                "start_date": result.get("startDate"),
                "due_date": result.get("dueDate"),
                "status": result.get("_links", {}).get("status", {}).get("title", "Unknown"),
                "type": result.get("_links", {}).get("type", {}).get("title"),
                "priority": result.get("_links", {}).get("priority", {}).get("title"),
                "version": _version_title(result),
                "sprint": _sprint_title(result),
                "url": f"{settings.openproject_url}/work_packages/{result.get('id')}"
            }
        }, indent=2)
        
    except ValidationError as e:
        return json.dumps({
            "success": False,
            "error": "Validation error",
            "details": [{"field": err["loc"][-1], "message": err["msg"]} for err in e.errors()]
        }, indent=2)
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def create_work_package_dependency(
    from_work_package_id: int,
    to_work_package_id: int,
    relation_type: str = "follows",
    description: str = "",
    lag: int = 0
) -> str:
    """Create a dependency between two work packages for Gantt chart visualization.
    
    Args:
        from_work_package_id: ID of the work package that comes first
        to_work_package_id: ID of the work package that depends on the first
        relation_type: Type of relation (follows, precedes, blocks, blocked, relates, duplicates, duplicated)
        description: Optional description of the relation
        lag: Working days between finish of predecessor and start of successor (default: 0)
    
    Returns:
        JSON string with relation creation result
    """
    try:
        # Create and validate relation request using Pydantic model
        relation_request = WorkPackageRelationCreateRequest(
            from_work_package_id=from_work_package_id,
            to_work_package_id=to_work_package_id,
            relation_type=relation_type,
            description=description,
            lag=lag
        )
        
        # Call OpenProject API
        result = await openproject_client.create_work_package_relation(
            relation_request.from_work_package_id, 
            relation_request.to_work_package_id, 
            relation_request.relation_type, 
            relation_request.description, 
            relation_request.lag
        )
        
        # Extract relation info from result
        relation_data = {
            "id": result.get("id"),
            "from_work_package_id": from_work_package_id,
            "to_work_package_id": to_work_package_id,
            "relation_type": result.get("type", relation_type),
            "reverse_type": result.get("reverseType"),
            "description": result.get("description", description),
            "lag": result.get("lag", lag),
            "url": f"{settings.openproject_url}/relations/{result.get('id')}" if result.get('id') else None
        }
        
        return json.dumps({
            "success": True,
            "message": f"Relation created: Work package {from_work_package_id} {relation_type} work package {to_work_package_id}",
            "relation": relation_data
        }, indent=2)
        
    except ValidationError as e:
        return json.dumps({
            "success": False,
            "error": "Validation error",
            "details": [{"field": err["loc"][-1], "message": err["msg"]} for err in e.errors()]
        }, indent=2)
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_work_package_relations(work_package_id: int) -> str:
    """Get all relations for a specific work package.
    
    Args:
        work_package_id: ID of the work package to get relations for
    
    Returns:
        JSON string with list of relations
    """
    try:
        if work_package_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Work package ID must be a positive integer"
            })
        
        relations = await openproject_client.get_work_package_relations(work_package_id)
        
        relation_list = []
        for relation in relations:
            # Extract linked work packages info
            from_wp = relation.get("_links", {}).get("from", {})
            to_wp = relation.get("_links", {}).get("to", {})
            
            relation_data = {
                "id": relation.get("id"),
                "type": relation.get("type"),
                "reverse_type": relation.get("reverseType"),
                "description": relation.get("description", ""),
                "lag": relation.get("lag", 0),
                "from_work_package": {
                    "id": from_wp.get("href", "").split("/")[-1] if from_wp.get("href") else None,
                    "title": from_wp.get("title", "Unknown")
                },
                "to_work_package": {
                    "id": to_wp.get("href", "").split("/")[-1] if to_wp.get("href") else None,
                    "title": to_wp.get("title", "Unknown")
                }
            }
            relation_list.append(relation_data)
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(relation_list)} relations for work package {work_package_id}",
            "work_package_id": work_package_id,
            "relations": relation_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def delete_work_package_relation(relation_id: int) -> str:
    """Delete a work package relation.
    
    Args:
        relation_id: ID of the relation to delete
    
    Returns:
        JSON string with deletion result
    """
    try:
        if relation_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Relation ID must be a positive integer"
            })
        
        await openproject_client.delete_work_package_relation(relation_id)
        
        return json.dumps({
            "success": True,
            "message": f"Relation {relation_id} deleted successfully"
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_projects() -> str:
    """Get list of all projects from OpenProject.
    
    Returns:
        JSON string with list of projects
    """
    try:
        projects = await openproject_client.get_projects()
        
        project_list = []
        for project in projects:
            project_list.append({
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", {}).get("raw", ""),
                "status": project.get("status"),
                "identifier": project.get("identifier"),
                "url": f"{settings.openproject_url}/projects/{project.get('identifier', project.get('id'))}"
            })
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(project_list)} projects",
            "projects": project_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_work_package(work_package_id: int) -> str:
    """Get all details of a specific work package by ID.

    Args:
        work_package_id: The ID of the work package to retrieve

    Returns:
        JSON string with work package details or error message
    """
    try:
        # T006: Input validation - work_package_id must be positive
        if work_package_id <= 0:
            log_tool_execution(logger, "get_work_package", False, work_package_id=work_package_id, error="Invalid ID")
            return json.dumps({
                "success": False,
                "error": "Work package ID must be a positive integer"
            })

        # T008: Log the operation
        logger.info(f"Retrieving work package with ID: {work_package_id}")

        # Call OpenProject API
        wp = await openproject_client.get_work_package_by_id(work_package_id)

        # T007: Parse HAL+JSON response and extract all fields per data-model.md
        # Extract project ID from href (e.g., "/api/v3/projects/5" -> 5)
        project_href = wp.get("_links", {}).get("project", {}).get("href", "")
        project_id = int(project_href.split("/")[-1]) if project_href else None

        # Parse ISO duration for estimated hours (e.g., "PT16H" -> 16.0)
        estimated_time = wp.get("estimatedTime")
        estimated_hours = None
        if estimated_time:
            estimated_hours = _parse_iso_duration(estimated_time)

        # Extract description from raw format
        description_obj = wp.get("description", {})
        description = description_obj.get("raw", "") if isinstance(description_obj, dict) else ""

        # Build response with all fields from data-model.md
        work_package_data = {
            "id": wp.get("id"),
            "subject": wp.get("subject"),
            "description": description,
            "status": wp.get("_links", {}).get("status", {}).get("title"),
            "type": wp.get("_links", {}).get("type", {}).get("title"),
            "priority": wp.get("_links", {}).get("priority", {}).get("title"),
            "version": _version_title(wp),
            "sprint": _sprint_title(wp),
            "assignee": wp.get("_links", {}).get("assignee", {}).get("title"),
            "responsible": wp.get("_links", {}).get("responsible", {}).get("title"),
            "project_id": project_id,
            "project_name": wp.get("_links", {}).get("project", {}).get("title"),
            "start_date": wp.get("startDate"),
            "due_date": wp.get("dueDate"),
            "estimated_hours": estimated_hours,
            "done_ratio": wp.get("percentageDone", 0),
            "created_at": wp.get("createdAt"),
            "updated_at": wp.get("updatedAt")
        }

        result = {
            "success": True,
            "work_package": work_package_data
        }

        log_tool_execution(logger, "get_work_package", True, work_package_id=work_package_id)
        return json.dumps(result, indent=2)

    except OpenProjectAPIError as e:
        # T011, T012: Handle specific error codes
        error_msg = str(e.message)

        if e.status_code == 404:
            error_msg = f"Work package with ID {work_package_id} not found"
        elif e.status_code == 403:
            error_msg = "Permission denied: You do not have access to view this work package"

        log_error(logger, e, {"tool": "get_work_package", "work_package_id": work_package_id})
        return json.dumps({
            "success": False,
            "error": error_msg
        }, indent=2)

    except Exception as e:
        # T013: Handle API connection failures and unexpected errors
        log_error(logger, e, {"tool": "get_work_package", "work_package_id": work_package_id})

        # Check if it's a connection error
        error_str = str(e).lower()
        if "connect" in error_str or "timeout" in error_str or "network" in error_str:
            return json.dumps({
                "success": False,
                "error": "Failed to connect to OpenProject. Please check your connection and try again."
            }, indent=2)

        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


def _parse_iso_duration(duration: str) -> float:
    """Parse ISO 8601 duration string to hours.

    Examples:
        PT16H -> 16.0
        PT1H30M -> 1.5
        PT30M -> 0.5
    """
    if not duration or not duration.startswith("PT"):
        return None

    hours = 0.0
    remaining = duration[2:]  # Remove "PT" prefix

    # Extract hours
    if "H" in remaining:
        h_idx = remaining.index("H")
        hours += float(remaining[:h_idx])
        remaining = remaining[h_idx + 1:]

    # Extract minutes and convert to hours
    if "M" in remaining:
        m_idx = remaining.index("M")
        minutes = float(remaining[:m_idx])
        hours += minutes / 60.0

    return hours


@app.tool()
async def get_work_packages(
    project_id: int,
    version: Optional[Union[str, int]] = None,
    sprint: Optional[Union[str, int]] = None,
    status: Optional[Union[str, int]] = "open",
    exclude_status: Optional[Union[str, int, List[Union[str, int]]]] = None,
    max_results: Optional[int] = 100
) -> str:
    """Get work packages for a specific project.
    
    Args:
        project_id: ID of the project to get work packages from
        version: Only return work packages in this version/milestone, given as
                 name (case-insensitive) or version ID (optional)
        sprint: Only return work packages planned into this sprint, given as
                name (case-insensitive) or sprint ID (optional). Sprints are
                separate from versions, even where their names match.
        status: "open" (default), "closed", "all", or a specific status name
                (case-insensitive) or status ID
        exclude_status: Status name(s) or ID(s) to leave out, as a single value
                        or a list (optional). Combines with status, e.g.
                        status="open", exclude_status="On hold".
        max_results: Maximum number of work packages to return (default 100).
                     Use null to return every matching work package.
    
    Returns:
        JSON string with list of work packages, the total number of matches,
        and whether the list was truncated by max_results
    """
    try:
        if project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })
        
        if max_results is not None and max_results <= 0:
            return json.dumps({
                "success": False,
                "error": "max_results must be a positive integer"
            })
        
        filters = []
        
        # OpenProject keeps only one filter per field, so status and
        # exclude_status must be merged into a single status filter.
        status_operators = {"open": "o", "closed": "c", "all": "*"}
        status_key = status.strip().lower() if isinstance(status, str) else status
        if status_key is None or status_key == "":
            status_key = "open"
        
        statuses = await openproject_client.get_work_package_statuses()
        if status_key in status_operators:
            selected = [
                s for s in statuses
                if status_key == "all" or s.get("isClosed", False) == (status_key == "closed")
            ]
        else:
            resolved_status = await _resolve_status(status)
            if not resolved_status:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid status '{status}'. Use 'open', 'closed', 'all' or one of: "
                             f"{_available_names(statuses)}"
                })
            selected = [resolved_status]
        
        excluded_ids = set()
        if exclude_status is not None and exclude_status != "":
            excluded = exclude_status if isinstance(exclude_status, list) else [exclude_status]
            for value in excluded:
                resolved_status = await _resolve_status(value)
                if not resolved_status:
                    return json.dumps({
                        "success": False,
                        "error": f"Invalid exclude_status '{value}'. Available statuses: "
                                 f"{_available_names(statuses)}"
                    })
                excluded_ids.add(str(resolved_status["id"]))
        
        if not excluded_ids and status_key in status_operators:
            filters.append({"status": {"operator": status_operators[status_key], "values": []}})
        elif status_key == "all":
            filters.append({"status": {"operator": "!", "values": sorted(excluded_ids)}})
        else:
            allowed_ids = [str(s["id"]) for s in selected if str(s["id"]) not in excluded_ids]
            if not allowed_ids:
                return json.dumps({
                    "success": True,
                    "message": f"Found 0 work packages in project {project_id} "
                               f"(every selected status is excluded)",
                    "total": 0,
                    "returned": 0,
                    "truncated": False,
                    "work_packages": []
                }, indent=2)
            filters.append({"status": {"operator": "=", "values": allowed_ids}})
        
        if version is not None and version != "":
            resolved_version = await _resolve_version(version, project_id)
            if not resolved_version:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid version '{version}' for project {project_id}. "
                             f"Available versions: {_available_names(await openproject_client.get_versions(project_id))}"
                })
            filters.append({"version": {"operator": "=", "values": [str(resolved_version["id"])]}})
        
        if sprint is not None and sprint != "":
            resolved_sprint = await _resolve_sprint(sprint, project_id)
            if not resolved_sprint:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid sprint '{sprint}' for project {project_id}. "
                             f"Available sprints: {_available_names(await openproject_client.get_sprints(project_id))}"
                })
            filters.append({"sprint": {"operator": "=", "values": [str(resolved_sprint["id"])]}})
        
        work_packages, total = await openproject_client.query_work_packages(
            project_id, filters=filters, max_results=max_results
        )
        
        wp_list = []
        for wp in work_packages:
            wp_list.append({
                "id": wp.get("id"),
                "subject": wp.get("subject"),
                "description": wp.get("description", {}).get("raw", ""),
                "project_id": project_id,
                "start_date": wp.get("startDate"),
                "due_date": wp.get("dueDate"),
                "status": wp.get("_links", {}).get("status", {}).get("title", "Unknown"),
                "assignee": wp.get("_links", {}).get("assignee", {}).get("title", "Unassigned"),
                "version": _version_title(wp),
                "sprint": _sprint_title(wp),
                "url": f"{settings.openproject_url}/work_packages/{wp.get('id')}"
            })
        
        truncated = len(wp_list) < total
        message = f"Found {total} work packages in project {project_id}"
        if truncated:
            message += f", returning the first {len(wp_list)} (raise max_results to get more)"
        
        return json.dumps({
            "success": True,
            "message": message,
            "total": total,
            "returned": len(wp_list),
            "truncated": truncated,
            "work_packages": wp_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def update_work_package(
    work_package_id: int,
    subject: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    assignee_id: Optional[int] = None,
    estimated_hours: Optional[float] = None,
    status: Optional[Union[str, int]] = None,
    version: Optional[Union[str, int]] = None,
    type: Optional[Union[str, int]] = None,
    priority: Optional[Union[str, int]] = None,
    sprint: Optional[Union[str, int]] = None
) -> str:
    """Update an existing work package.

    Args:
        work_package_id: ID of the work package to update
        subject: New subject/title (optional)
        description: New description (optional)
        start_date: New start date in YYYY-MM-DD format (optional)
        due_date: New due date in YYYY-MM-DD format (optional)
        assignee_id: User ID to assign work package to (optional)
        estimated_hours: New estimated hours (optional)
        status: Status name (string, case-insensitive) or status ID (integer) (optional)
        version: Version/milestone name (string, case-insensitive) or version ID
                 (integer) to assign the work package to (optional)
        type: Type name (e.g. "Task", "Bug", "Milestone") or type ID (optional)
        priority: Priority name (e.g. "High") or priority ID (optional)
        sprint: Sprint name (string, case-insensitive) or sprint ID (integer) to
                plan the work package into (optional). Sprints are separate from
                versions; setting one does not set the other.

    Returns:
        JSON string with update result
    """
    try:
        if work_package_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Work package ID must be a positive integer"
            })
        
        # Build update payload with only provided fields
        updates = {}
        
        if subject:
            updates["subject"] = subject.strip()
        
        if description is not None:
            updates["description"] = {"raw": description.strip()}
        
        if start_date:
            if not _is_valid_date_format(start_date):
                return json.dumps({
                    "success": False,
                    "error": "Start date must be in YYYY-MM-DD format"
                })
            updates["startDate"] = start_date
        
        if due_date:
            if not _is_valid_date_format(due_date):
                return json.dumps({
                    "success": False,
                    "error": "Due date must be in YYYY-MM-DD format"
                })
            updates["dueDate"] = due_date
        
        if assignee_id:
            updates["_links"] = updates.get("_links", {})
            updates["_links"]["assignee"] = {"href": f"/api/v3/users/{assignee_id}"}
        
        if estimated_hours:
            updates["estimatedTime"] = f"PT{estimated_hours}H"

        # Type, version and sprint names are only meaningful within a project, so
        # resolving one by name needs the work package's own project. Fetch the
        # work package at most once for that, reusing its lockVersion to avoid a
        # second round trip inside the client.
        wp_project = {}
        
        async def project_scope():
            if "id" not in wp_project:
                wp = await openproject_client.get_work_package_by_id(work_package_id)
                updates.setdefault("lockVersion", wp.get("lockVersion"))
                project_href = wp.get("_links", {}).get("project", {}).get("href", "")
                try:
                    wp_project["id"] = int(project_href.split("/")[-1])
                except (ValueError, IndexError):
                    wp_project["id"] = None
            return wp_project["id"]
        
        # Resolve the named fields to their API links
        for field, value, path, scoped, resolve, fetch_available in (
            ("status", status, "statuses", False,
             lambda v, p: _resolve_status(v),
             lambda p: openproject_client.get_work_package_statuses()),
            ("type", type, "types", True,
             lambda v, p: _resolve_type(v, p),
             lambda p: openproject_client.get_work_package_types(p)),
            ("priority", priority, "priorities", False,
             lambda v, p: _resolve_priority(v),
             lambda p: openproject_client.get_priorities()),
            ("version", version, "versions", True,
             lambda v, p: _resolve_version(v, p),
             lambda p: openproject_client.get_versions(p)),
            ("sprint", sprint, "sprints", True,
             lambda v, p: _resolve_sprint(v, p),
             lambda p: openproject_client.get_sprints(p)),
        ):
            if value is None or value == "":
                continue
            
            # Only a project-scoped lookup by name needs the project
            project_id = await project_scope() if scoped and isinstance(value, str) else None
            
            resolved = await resolve(value, project_id)
            if not resolved:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid {field} '{value}'. "
                             f"Available {field}s: {_available_names(await fetch_available(project_id))}"
                })
            
            updates["_links"] = updates.get("_links", {})
            if field == "version":
                updates["_links"].update(OpenProjectClient.version_links(resolved["id"]))
            else:
                updates["_links"][field] = {"href": f"/api/v3/{path}/{resolved['id']}"}

        if not updates:
            return json.dumps({
                "success": False,
                "error": "No updates provided. Specify at least one field to update."
            })
        
        result = await openproject_client.update_work_package(work_package_id, updates)

        # Extract is_closed from status metadata
        is_closed = None
        status_href = result.get("_links", {}).get("status", {}).get("href", "")
        if status_href:
            # Extract status ID from href (e.g., "/api/v3/statuses/2" -> 2)
            try:
                status_id = int(status_href.split("/")[-1])
                statuses = await openproject_client.get_work_package_statuses()
                matched_status = next((s for s in statuses if s.get("id") == status_id), None)
                if matched_status:
                    is_closed = matched_status.get("isClosed", False)
            except (ValueError, IndexError):
                pass

        return json.dumps({
            "success": True,
            "message": f"Work package {work_package_id} updated successfully",
            "work_package": {
                "id": result.get("id"),
                "subject": result.get("subject"),
                "description": result.get("description", {}).get("raw", ""),
                "start_date": result.get("startDate"),
                "due_date": result.get("dueDate"),
                "status": result.get("_links", {}).get("status", {}).get("title", "Unknown"),
                "is_closed": is_closed,
                "type": result.get("_links", {}).get("type", {}).get("title"),
                "priority": result.get("_links", {}).get("priority", {}).get("title"),
                "version": _version_title(result),
                "sprint": _sprint_title(result),
                "url": f"{settings.openproject_url}/work_packages/{result.get('id')}"
            }
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_users(email_filter: Optional[str] = None) -> str:
    """Get list of users, optionally filtered by email.
    
    Args:
        email_filter: Optional email address to search for specific user
    
    Returns:
        JSON string with list of users
    """
    try:
        filters = None
        if email_filter:
            # OpenProject API filter format for email search
            filters = {"filters": f'[{{"email": {{"operator": "=", "values": ["{email_filter}"]}}}}]'}
        
        users = await openproject_client.get_users(filters)
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.get("id"),
                "name": user.get("name"),
                "firstName": user.get("firstName", ""),
                "lastName": user.get("lastName", ""),
                "email": user.get("email", ""),
                "login": user.get("login", ""),
                "status": user.get("status", ""),
                "language": user.get("language", ""),
                "admin": user.get("admin", False),
                "created_at": user.get("createdAt", ""),
                "updated_at": user.get("updatedAt", "")
            })
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(user_list)} users" + (f" matching email '{email_filter}'" if email_filter else ""),
            "users": user_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def assign_work_package_by_email(work_package_id: int, assignee_email: str) -> str:
    """Assign work package to user by email address.
    
    Args:
        work_package_id: ID of the work package to assign
        assignee_email: Email address of the user to assign to
    
    Returns:
        JSON string with assignment result
    """
    try:
        if work_package_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Work package ID must be a positive integer"
            })
        
        if not assignee_email or "@" not in assignee_email:
            return json.dumps({
                "success": False,
                "error": "Valid email address is required"
            })
        
        # Find user by email
        user = await openproject_client.get_user_by_email(assignee_email)
        if not user:
            return json.dumps({
                "success": False,
                "error": f"User with email '{assignee_email}' not found"
            })
        
        # Update work package with assignee
        updates = {
            "_links": {
                "assignee": {
                    "href": f"/api/v3/users/{user.get('id')}"
                }
            }
        }
        
        result = await openproject_client.update_work_package(work_package_id, updates)
        
        return json.dumps({
            "success": True,
            "message": f"Work package {work_package_id} assigned to {user.get('name', assignee_email)}",
            "work_package": {
                "id": result.get("id"),
                "subject": result.get("subject"),
                "assignee": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "email": user.get("email")
                },
                "url": f"{settings.openproject_url}/work_packages/{result.get('id')}"
            }
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_project_members(project_id: int) -> str:
    """Get list of project members with roles.
    
    Args:
        project_id: ID of the project to get members from
    
    Returns:
        JSON string with list of project members
    """
    try:
        if project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })
        
        memberships = await openproject_client.get_project_memberships(project_id)
        
        member_list = []
        for membership in memberships:
            # Extract user and role information from HAL+JSON structure
            user_link = membership.get("_links", {}).get("principal", {})
            roles = membership.get("_links", {}).get("roles", [])
            
            # Get user details if available
            user_info = {
                "id": user_link.get("href", "").split("/")[-1] if user_link.get("href") else None,
                "title": user_link.get("title", "Unknown User")
            }
            
            # Extract role names
            role_names = []
            if isinstance(roles, list):
                role_names = [role.get("title", "Unknown Role") for role in roles]
            elif isinstance(roles, dict):
                role_names = [roles.get("title", "Unknown Role")]
            
            member_data = {
                "id": membership.get("id"),
                "user": user_info,
                "roles": role_names,
                "created_at": membership.get("createdAt", ""),
                "updated_at": membership.get("updatedAt", "")
            }
            member_list.append(member_data)
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(member_list)} members in project {project_id}",
            "project_id": project_id,
            "members": member_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_work_package_types(project_id: Optional[int] = None) -> str:
    """Get available work package types from OpenProject.
    
    Args:
        project_id: Restrict results to the types enabled for this project
                    (optional). Types are defined instance-wide, but each
                    project enables only a subset of them.
    
    Returns:
        JSON string with list of work package types
    """
    try:
        if project_id is not None and project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })
        
        types = await openproject_client.get_work_package_types(project_id)
        
        type_list = []
        for wp_type in types:
            type_list.append({
                "id": wp_type.get("id"),
                "name": wp_type.get("name"),
                "description": wp_type.get("description", ""),
                "position": wp_type.get("position", 0),
                "is_default": wp_type.get("isDefault", False),
                "is_milestone": wp_type.get("isMilestone", False)
            })
        
        scope = f" in project {project_id}" if project_id else ""
        return json.dumps({
            "success": True,
            "message": f"Found {len(type_list)} work package types{scope}",
            "types": type_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_versions(project_id: Optional[int] = None) -> str:
    """Get available versions (releases/milestones) from OpenProject.

    Args:
        project_id: Restrict results to this project's versions (optional).
                    Version names are only unique per project, so pass this when
                    looking up a name to assign to a work package.

    Returns:
        JSON string with list of versions
    """
    try:
        if project_id is not None and project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })

        versions = await openproject_client.get_versions(project_id)

        version_list = []
        for version in versions:
            version_list.append({
                "id": version.get("id"),
                "name": version.get("name"),
                "description": version.get("description", {}).get("raw", ""),
                "status": version.get("status", ""),
                "start_date": version.get("startDate"),
                "end_date": version.get("endDate"),
                "sharing": version.get("sharing", ""),
                "project": version.get("_links", {}).get("definingProject", {}).get("title", "")
            })

        scope = f" in project {project_id}" if project_id else ""
        return json.dumps({
            "success": True,
            "message": f"Found {len(version_list)} versions{scope}",
            "versions": version_list
        }, indent=2)

    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_sprints(project_id: Optional[int] = None) -> str:
    """Get sprints from OpenProject.

    Sprints are separate from versions: a work package has its own sprint
    field, and sprint IDs differ from version IDs even where names match.

    Args:
        project_id: Restrict results to the sprints available to this project
                    (optional). Pass this when looking up a sprint name to plan
                    a work package into.

    Returns:
        JSON string with list of sprints
    """
    try:
        if project_id is not None and project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })

        sprints = await openproject_client.get_sprints(project_id)

        sprint_list = []
        for sprint in sprints:
            links = sprint.get("_links", {})
            sprint_list.append({
                "id": sprint.get("id"),
                "name": sprint.get("name"),
                "status": (links.get("status") or {}).get("title"),
                "start_date": sprint.get("startDate"),
                "finish_date": sprint.get("finishDate"),
                "project": (links.get("definingWorkspace") or {}).get("title")
            })

        scope = f" in project {project_id}" if project_id else ""
        return json.dumps({
            "success": True,
            "message": f"Found {len(sprint_list)} sprints{scope}",
            "sprints": sprint_list
        }, indent=2)

    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_work_package_statuses() -> str:
    """Get available work package statuses from OpenProject.
    
    Returns:
        JSON string with list of work package statuses
    """
    try:
        statuses = await openproject_client.get_work_package_statuses()
        
        status_list = []
        for status in statuses:
            status_list.append({
                "id": status.get("id"),
                "name": status.get("name"),
                "description": status.get("description", ""),
                "position": status.get("position", 0),
                "is_default": status.get("isDefault", False),
                "is_closed": status.get("isClosed", False),
                "is_readonly": status.get("isReadonly", False)
            })
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(status_list)} work package statuses",
            "statuses": status_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_priorities() -> str:
    """Get available work package priorities from OpenProject.
    
    Returns:
        JSON string with list of priorities
    """
    try:
        priorities = await openproject_client.get_priorities()
        
        priority_list = []
        for priority in priorities:
            priority_list.append({
                "id": priority.get("id"),
                "name": priority.get("name"),
                "description": priority.get("description", ""),
                "position": priority.get("position", 0),
                "is_default": priority.get("isDefault", False),
                "is_active": priority.get("isActive", True)
            })
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(priority_list)} priorities",
            "priorities": priority_list
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


@app.tool()
async def get_project_summary(project_id: int) -> str:
    """Get a comprehensive summary of a project including work packages and status.
    
    Args:
        project_id: ID of the project to summarize
    
    Returns:
        JSON string with project summary
    """
    try:
        if project_id <= 0:
            return json.dumps({
                "success": False,
                "error": "Project ID must be a positive integer"
            })
        
        # Get project details and work packages in parallel
        projects = await openproject_client.get_projects()
        project = next((p for p in projects if p.get("id") == project_id), None)
        
        if not project:
            return json.dumps({
                "success": False,
                "error": f"Project with ID {project_id} not found"
            })
        
        work_packages = await openproject_client.get_work_packages(project_id)
        
        # Analyze work packages
        total_wp = len(work_packages)
        with_dates = sum(1 for wp in work_packages if wp.get("startDate") or wp.get("dueDate"))
        assigned = sum(1 for wp in work_packages if wp.get("_links", {}).get("assignee"))
        
        status_counts = {}
        for wp in work_packages:
            status = wp.get("_links", {}).get("status", {}).get("title", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return json.dumps({
            "success": True,
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", {}).get("raw", ""),
                "status": project.get("status"),
                "url": f"{settings.openproject_url}/projects/{project.get('identifier', project.get('id'))}"
            },
            "summary": {
                "total_work_packages": total_wp,
                "work_packages_with_dates": with_dates,
                "assigned_work_packages": assigned,
                "unassigned_work_packages": total_wp - assigned,
                "status_breakdown": status_counts,
                "gantt_ready": with_dates > 0
            }
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "success": False,
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


def _is_valid_date_format(date_string: str) -> bool:
    """Validate date string is in YYYY-MM-DD format."""
    try:
        from datetime import datetime
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# Add resource handlers
@app.resource("openproject://projects")
async def projects_resource() -> str:
    """List all projects in OpenProject."""
    try:
        projects = await openproject_client.get_projects()
        
        formatted_projects = []
        for project in projects:
            formatted_projects.append({
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", {}).get("raw", ""),
                "status": project.get("status"),
                "identifier": project.get("identifier"),
                "url": f"{settings.openproject_url}/projects/{project.get('identifier', project.get('id'))}"
            })
        
        return json.dumps({
            "projects": formatted_projects,
            "total": len(formatted_projects),
            "retrieved_at": "now"
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)


@app.resource("openproject://project/{project_id}")
async def project_resource(project_id: int) -> str:
    """Get details for a specific project."""
    try:
        projects = await openproject_client.get_projects()
        project = next((p for p in projects if p.get("id") == project_id), None)
        
        if not project:
            return json.dumps({
                "error": f"Project with ID {project_id} not found"
            }, indent=2)
        
        # Get work packages for this project
        work_packages = await openproject_client.get_work_packages(project_id)
        
        return json.dumps({
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", {}).get("raw", ""),
                "status": project.get("status"),
                "identifier": project.get("identifier"),
                "url": f"{settings.openproject_url}/projects/{project.get('identifier', project.get('id'))}"
            },
            "work_packages_count": len(work_packages),
            "retrieved_at": "now"
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)


@app.resource("openproject://work-packages/{project_id}")
async def work_packages_resource(project_id: int) -> str:
    """Get work packages for a specific project."""
    try:
        work_packages = await openproject_client.get_work_packages(project_id)
        
        formatted_wps = []
        for wp in work_packages:
            formatted_wps.append({
                "id": wp.get("id"),
                "subject": wp.get("subject"),
                "description": wp.get("description", {}).get("raw", ""),
                "project_id": project_id,
                "start_date": wp.get("startDate"),
                "due_date": wp.get("dueDate"),
                "status": wp.get("_links", {}).get("status", {}).get("title", "Unknown"),
                "type": wp.get("_links", {}).get("type", {}).get("title", "Unknown"),
                "priority": wp.get("_links", {}).get("priority", {}).get("title", "Unknown"),
                "assignee": wp.get("_links", {}).get("assignee", {}).get("title", "Unassigned"),
                "url": f"{settings.openproject_url}/work_packages/{wp.get('id')}"
            })
        
        return json.dumps({
            "work_packages": formatted_wps,
            "project_id": project_id,
            "total": len(formatted_wps),
            "retrieved_at": "now"
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)


@app.resource("openproject://work-package/{work_package_id}")
async def work_package_resource(work_package_id: int) -> str:
    """Get details for a specific work package."""
    try:
        work_package = await openproject_client.get_work_package_by_id(work_package_id)
        
        return json.dumps({
            "work_package": {
                "id": work_package.get("id"),
                "subject": work_package.get("subject"),
                "description": work_package.get("description", {}).get("raw", ""),
                "project": work_package.get("_links", {}).get("project", {}).get("title", "Unknown"),
                "start_date": work_package.get("startDate"),
                "due_date": work_package.get("dueDate"),
                "status": work_package.get("_links", {}).get("status", {}).get("title", "Unknown"),
                "type": work_package.get("_links", {}).get("type", {}).get("title", "Unknown"),
                "priority": work_package.get("_links", {}).get("priority", {}).get("title", "Unknown"),
                "assignee": work_package.get("_links", {}).get("assignee", {}).get("title", "Unassigned"),
                "estimated_time": work_package.get("estimatedTime"),
                "done_ratio": work_package.get("doneRatio", 0),
                "url": f"{settings.openproject_url}/work_packages/{work_package.get('id')}"
            },
            "retrieved_at": "now"
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)


@app.resource("openproject://work-package-relations/{work_package_id}")
async def work_package_relations_resource(work_package_id: int) -> str:
    """Get relations for a specific work package."""
    try:
        relations = await openproject_client.get_work_package_relations(work_package_id)
        
        formatted_relations = []
        for relation in relations:
            # Extract linked work packages info
            from_wp = relation.get("_links", {}).get("from", {})
            to_wp = relation.get("_links", {}).get("to", {})
            
            relation_data = {
                "id": relation.get("id"),
                "type": relation.get("type"),
                "reverse_type": relation.get("reverseType"),
                "description": relation.get("description", ""),
                "lag": relation.get("lag", 0),
                "from_work_package": {
                    "id": from_wp.get("href", "").split("/")[-1] if from_wp.get("href") else None,
                    "title": from_wp.get("title", "Unknown")
                },
                "to_work_package": {
                    "id": to_wp.get("href", "").split("/")[-1] if to_wp.get("href") else None,
                    "title": to_wp.get("title", "Unknown")
                }
            }
            formatted_relations.append(relation_data)
        
        return json.dumps({
            "work_package_id": work_package_id,
            "relations": formatted_relations,
            "total": len(formatted_relations),
            "retrieved_at": "now"
        }, indent=2)
        
    except OpenProjectAPIError as e:
        return json.dumps({
            "error": f"OpenProject API error: {e.message}",
            "details": e.response_data
        }, indent=2)


# Add prompt handlers
@app.prompt()
async def project_status_report(project_id: int) -> list:
    """Generate a comprehensive project status report.
    
    Args:
        project_id: ID of the project to report on
        
    Returns:
        List of message objects for LLM consumption
    """
    try:
        # Get project details and work packages
        projects = await openproject_client.get_projects()
        project = next((p for p in projects if p.get("id") == project_id), None)
        
        if not project:
            return [
                {
                    "role": "user",
                    "content": f"Error: Project with ID {project_id} not found. Please check the project ID and try again."
                }
            ]
        
        work_packages = await openproject_client.get_work_packages(project_id)
        
        # Analyze project status
        total_wp = len(work_packages)
        with_dates = sum(1 for wp in work_packages if wp.get("startDate") or wp.get("dueDate"))
        assigned = sum(1 for wp in work_packages if wp.get("_links", {}).get("assignee"))
        
        status_counts = {}
        for wp in work_packages:
            status = wp.get("_links", {}).get("status", {}).get("title", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        project_data = {
            "project": {
                "name": project.get("name"),
                "description": project.get("description", {}).get("raw", ""),
                "status": project.get("status"),
                "url": f"{settings.openproject_url}/projects/{project.get('identifier', project.get('id'))}"
            },
            "summary": {
                "total_work_packages": total_wp,
                "work_packages_with_dates": with_dates,
                "assigned_work_packages": assigned,
                "unassigned_work_packages": total_wp - assigned,
                "status_breakdown": status_counts,
                "gantt_ready": with_dates > 0
            },
            "work_packages": [
                {
                    "subject": wp.get("subject"),
                    "status": wp.get("_links", {}).get("status", {}).get("title", "Unknown"),
                    "assignee": wp.get("_links", {}).get("assignee", {}).get("title", "Unassigned"),
                    "start_date": wp.get("startDate"),
                    "due_date": wp.get("dueDate")
                }
                for wp in work_packages[:10]  # Limit to first 10 for readability
            ]
        }
        
        return [
            {
                "role": "user",
                "content": f"""Please analyze this project status data and provide a comprehensive report:

{json.dumps(project_data, indent=2)}

Focus on:
1. Overall project health and progress
2. Work package completion status
3. Resource allocation (assigned vs unassigned work)
4. Timeline readiness (work packages with dates)
5. Any potential issues or recommendations
6. Next steps for project management"""
            }
        ]
        
    except Exception as e:
        return [
            {
                "role": "user",
                "content": f"Error generating project status report: {str(e)}"
            }
        ]


@app.prompt()
async def work_package_summary(project_id: int, status_filter: str = "all") -> list:
    """Summarize work packages in a project.
    
    Args:
        project_id: ID of the project
        status_filter: Filter by status (all, new, in_progress, closed, etc.)
        
    Returns:
        List of message objects for LLM consumption
    """
    try:
        work_packages = await openproject_client.get_work_packages(project_id)
        
        # Filter by status if specified
        if status_filter != "all":
            work_packages = [
                wp for wp in work_packages 
                if wp.get("_links", {}).get("status", {}).get("title", "").lower() == status_filter.lower()
            ]
        
        wp_data = []
        for wp in work_packages:
            wp_data.append({
                "id": wp.get("id"),
                "subject": wp.get("subject"),
                "description": wp.get("description", {}).get("raw", "")[:200] + "..." if len(wp.get("description", {}).get("raw", "")) > 200 else wp.get("description", {}).get("raw", ""),
                "status": wp.get("_links", {}).get("status", {}).get("title", "Unknown"),
                "type": wp.get("_links", {}).get("type", {}).get("title", "Unknown"),
                "priority": wp.get("_links", {}).get("priority", {}).get("title", "Unknown"),
                "assignee": wp.get("_links", {}).get("assignee", {}).get("title", "Unassigned"),
                "start_date": wp.get("startDate"),
                "due_date": wp.get("dueDate"),
                "done_ratio": wp.get("doneRatio", 0)
            })
        
        return [
            {
                "role": "user",
                "content": f"""Please provide a summary of these work packages (filtered by status: {status_filter}):

{json.dumps(wp_data, indent=2)}

Please organize your summary by:
1. High-priority items requiring attention
2. Items by status category
3. Timeline overview (upcoming deadlines)
4. Resource allocation analysis
5. Recommendations for project management"""
            }
        ]
        
    except Exception as e:
        return [
            {
                "role": "user",
                "content": f"Error generating work package summary: {str(e)}"
            }
        ]


@app.prompt()
async def project_planning_assistant(project_name: str, work_package_count: int = 5) -> list:
    """Help with planning a new project structure.
    
    Args:
        project_name: Name of the project to plan
        work_package_count: Suggested number of work packages to create
        
    Returns:
        List of message objects for LLM consumption
    """
    return [
        {
            "role": "user",
            "content": f"""I need help planning a new project called "{project_name}". 

Please help me create a project structure with approximately {work_package_count} work packages. Consider:

1. **Project Planning Best Practices:**
   - Break down the project into logical phases
   - Create work packages with clear deliverables
   - Establish realistic timelines
   - Define dependencies between work packages

2. **For Each Work Package, suggest:**
   - Clear, actionable title
   - Brief description of what needs to be done
   - Estimated duration
   - Dependencies on other work packages
   - Priority level

3. **Timeline Considerations:**
   - Logical sequence of work packages
   - Dependencies that affect scheduling
   - Buffer time for unexpected issues
   - Milestone checkpoints

4. **Resource Planning:**
   - Skills required for each work package
   - Potential team member assignments
   - External dependencies or resources needed

Please provide a structured breakdown that I can use to create the project in OpenProject with proper dates and dependencies for a functional Gantt chart."""
        }
    ]


@app.prompt()
async def team_workload_analysis(project_ids: list[int] = None) -> list:
    """Analyze team workload across projects.
    
    Args:
        project_ids: List of project IDs to analyze (optional, analyzes all if not provided)
        
    Returns:
        List of message objects for LLM consumption
    """
    try:
        # Get all projects if none specified
        if project_ids is None:
            projects = await openproject_client.get_projects()
            project_ids = [p.get("id") for p in projects[:5]]  # Limit to first 5 for performance
        
        workload_data = {}
        total_work_packages = 0
        
        for project_id in project_ids:
            try:
                work_packages = await openproject_client.get_work_packages(project_id)
                total_work_packages += len(work_packages)
                
                for wp in work_packages:
                    assignee = wp.get("_links", {}).get("assignee", {}).get("title", "Unassigned")
                    if assignee not in workload_data:
                        workload_data[assignee] = {
                            "total_tasks": 0,
                            "in_progress": 0,
                            "completed": 0,
                            "overdue": 0,
                            "projects": set()
                        }
                    
                    workload_data[assignee]["total_tasks"] += 1
                    workload_data[assignee]["projects"].add(project_id)
                    
                    status = wp.get("_links", {}).get("status", {}).get("title", "").lower()
                    if "progress" in status or "active" in status:
                        workload_data[assignee]["in_progress"] += 1
                    elif "closed" in status or "done" in status:
                        workload_data[assignee]["completed"] += 1
                    
                    # Check for overdue items (simplified check)
                    due_date = wp.get("dueDate")
                    if due_date and due_date < "2024-12-20":  # Simplified date check
                        workload_data[assignee]["overdue"] += 1
                        
            except Exception:
                continue  # Skip projects that can't be accessed
        
        # Convert sets to lists for JSON serialization
        for assignee_data in workload_data.values():
            assignee_data["projects"] = list(assignee_data["projects"])
        
        return [
            {
                "role": "user",
                "content": f"""Please analyze this team workload data across {len(project_ids)} projects:

Total work packages analyzed: {total_work_packages}

Team workload breakdown:
{json.dumps(workload_data, indent=2)}

Please provide analysis on:
1. **Workload Distribution:**
   - Who has the heaviest workload?
   - Are there team members with capacity for additional work?
   - Is work evenly distributed?

2. **Progress Analysis:**
   - Which team members are making good progress?
   - Are there bottlenecks or blockers?
   - Completion rates by team member

3. **Risk Assessment:**
   - Overdue items and their impact
   - Team members who might be overloaded
   - Projects that might need additional resources

4. **Recommendations:**
   - Workload rebalancing suggestions
   - Priority adjustments
   - Resource allocation improvements
   - Process improvements to increase efficiency"""
            }
        ]
        
    except Exception as e:
        return [
            {
                "role": "user",
                "content": f"Error generating team workload analysis: {str(e)}"
            }
        ]


# Server is run directly via app.run() from the run_server.py script
