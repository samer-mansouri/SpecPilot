# SpecPilot

SpecPilot is an interactive CLI developer tool for OpenAPI-driven API automation and inspection.

## Overview

SpecPilot parses OpenAPI 3.x specifications to discover endpoints, parameters, request/response models, and security definitions, providing CLI commands for specification analysis and inspection.

## Current Status

SpecPilot is in active development (`v0.1.0-dev`). Specification loading and normalization of OpenAPI 3.x documents (operations, paths, HTTP methods, `$ref` resolution, parameters, schemas, and security metadata) are fully implemented.

## Features

- Parse OpenAPI 3.x specifications (JSON and YAML).
- Load specifications from local file paths and remote HTTP/HTTPS URLs with timeout handling.
- Resolve local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`).
- Normalize operations, parameters, request bodies, responses, tags, servers, and security definitions into typed models.
- Actionable error reporting for missing files, network failures, timeouts, malformed documents, and unresolvable references.



## Installation

Ensure Python 3.10+ and `uv` (or `pip`) are installed.

```bash
# Editable install using uv
uv pip install -e .

# Or using standard pip
pip install -e .
```

## Quick Start

```bash
# Inspect an OpenAPI specification summary
specpilot import ./openapi.yaml

# List discovered endpoints and operations
specpilot endpoints ./openapi.yaml
```

## Architecture

```text
+--------------------------------------------------------+
|                      SpecPilot CLI                     |
|                (specpilot import/endpoints)            |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                    OpenAPI Loader                      |
|            (Local JSON/YAML & HTTP/HTTPS)              |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                    OpenAPI Parser                      |
|      (Normalization, Schema & $ref Resolution)         |
+--------------------------------------------------------+
```

## Supported OpenAPI Features

- OpenAPI 3.0.x and 3.1.x specifications.
- Local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`).
- Standard HTTP methods: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `HEAD`.

## Development

Run tests using `pytest`:

```bash
uv run pytest
```

## Roadmap

- **Milestone 1**: OpenAPI Core foundation (Current)
- **Milestone 2**: Dynamic MCP Tools
- **Milestone 3**: Agentic Workflows & Multi-Step Execution
- **Milestone 4**: Safety & Human Approval
- **Milestone 5**: Contract & API Testing
- **Milestone 6**: CLI Polish & Interactive Shell
- **Milestone 7**: Production Packaging & 1.0 Release

## Version

Current version: `0.1.0`
