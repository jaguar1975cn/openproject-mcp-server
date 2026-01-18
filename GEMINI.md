# OpenProject MCP Server Context

## Project Overview
This project is a **FastMCP-powered server** designed to enable AI assistants (like Claude and Gemini) to interact with **OpenProject** installations. It acts as a bridge, allowing the AI to manage projects, work packages, users, and dependencies directly through natural language commands.

**Key Features:**
*   **Project Management:** Create projects, work packages (tasks), and manage dependencies.
*   **Gantt Chart Support:** Specifically designed to enable the creation of functional Gantt charts in OpenProject by handling dates and task relations.
*   **User Management:** Find and assign users by email.
*   **Dynamic Configuration:** Auto-loads work package types, statuses, and priorities from the OpenProject instance.

## Architecture & Core Components
The project is built with **Python 3.8+** and uses the **FastMCP** framework.

*   **`src/mcp_server.py`**: The main entry point and FastMCP application definition. Contains all tool definitions (`create_project`, `get_work_packages`, etc.).
*   **`src/openproject_client.py`**: An asynchronous API client using `httpx`. Handles all communication with the OpenProject v3 API (HAL+JSON).
*   **`src/config.py`**: Manages configuration via environment variables (using `pydantic-settings` style or similar).
*   **`src/models.py`**: Pydantic models for data validation and typing of OpenProject resources (Projects, WorkPackages, Users).
*   **`src/handlers/`**: specific resource handlers (e.g., `resources.py`).
*   **`scripts/`**: Utility scripts for deployment (`deploy.sh`), testing (`test_mvp.py`), and running the server (`run_server.py`).

**Design Patterns:**
*   **Async-First:** All network I/O is asynchronous.
*   **Single Client:** A shared `OpenProjectClient` instance is used throughout the application lifecycle.
*   **Caching:** Implements a 5-minute TTL cache for static configuration data (types, statuses).

## Setup & Installation

### Prerequisites
*   Python 3.8+
*   A running OpenProject instance
*   An OpenProject API Key

### Quick Start
1.  **Clone & Venv:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Setup:**
    ```bash
    cp env.example .env
    # Edit .env with OPENPROJECT_URL and OPENPROJECT_API_KEY
    ```

## Running the Server

*   **Local Development:**
    ```bash
    python3 scripts/run_server.py
    ```
    *Note: Ensure `OPENPROJECT_URL` and `OPENPROJECT_API_KEY` are set in your environment or `.env` file.*

*   **Production (Docker):**
    The recommended way to run the server is via Docker, ensuring port consistency with your MCP client configuration.
    ```bash
    ./scripts/deploy.sh deploy 39127  # Deploys on port 39127
    ```

## Testing & Validation

The project includes both MVP validation scripts and a full test suite.

*   **Quick MVP Test:**
    Validates connection and core functionality (project/task creation).
    ```bash
    python3 scripts/test_mvp.py
    ```

*   **Run All Tests:**
    ```bash
    python3 tests/run_tests.py
    # OR using pytest directly
    python3 -m pytest tests/
    ```

*   **Specific Tests:**
    ```bash
    python3 -m pytest tests/test_api_compliance.py -v
    python3 -m pytest --cov=src tests/  # With coverage report
    ```

## Docker Deployment
Docker is the preferred deployment method. The `scripts/deploy.sh` script handles most operations.

*   **Deploy:** `./scripts/deploy.sh deploy [PORT]`
*   **Logs:** `./scripts/deploy.sh logs`
*   **Stop:** `./scripts/deploy.sh stop`
*   **Status:** `./scripts/deploy.sh status`

**Environment Variables for Docker:**
*   `OPENPROJECT_URL`: URL of the OpenProject instance (e.g., `http://localhost:8080`).
*   `OPENPROJECT_API_KEY`: Your API key.
*   `MCP_HOST`: Internal bind address (use `0.0.0.0` for Docker).
*   `MCP_PORT`: Internal port (default `8080`).

## Development Conventions
*   **Code Style:** Follow PEP 8.
*   **Type Hinting:** Use Python type hints extensively.
*   **Validation:** Use Pydantic models for all data structures exchanged with the API.
*   **Error Handling:** Parse OpenProject's HAL+JSON error responses and provide meaningful feedback.
*   **Testing:** Maintain high test coverage. New features should include unit and integration tests.
*   **Documentation:** Update `README.md` and `CLAUDE.md` when adding new tools or changing architecture.
