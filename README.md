# SpecPilot

SpecPilot is an interactive CLI developer tool for OpenAPI-driven API automation, inspection, and contract testing.

## Overview

SpecPilot parses OpenAPI 3.x specifications to discover endpoints, parameters, request/response models, and security definitions, dynamically converts API operations into Model Context Protocol (MCP) tools, provides CLI commands for inspection and tool execution, and executes automated API contract validation suites.

## Current Status

SpecPilot version `v0.6.0` features OpenAPI specification loading, OpenAPI normalization, MCP tool generation, HTTP tool execution, an interactive REPL shell (`specpilot shell`), LangGraph multi-step agent workflows, deterministic safety classification, human-in-the-loop approval controls, and OpenAPI-driven API contract testing.

## Features

- Parse OpenAPI 3.x specifications (JSON and YAML).
- Load specifications from local file paths and remote HTTP/HTTPS URLs with timeout handling.
- Resolve local `$ref` pointers (e.g. `#/components/schemas/...`).
- Normalize operations, parameters, request bodies, responses, tags, servers, and security definitions into typed Pydantic models.
- Dynamic conversion of OpenAPI operations into callable Model Context Protocol (MCP) tools.
- Automatic tool input JSON Schema generation covering path, query, header parameters, and JSON request bodies.
- HTTP tool execution engine supporting path substitution, query parameters, header mapping, body serialization, and secret redaction.
- Persistent interactive REPL shell (`specpilot shell`) supporting slash commands and natural-language instructions with tab-autocompletion.
- LangGraph stateful agent workflow (`SpecPilotGraph`) executing multi-step API workflows (e.g., list products -> select product -> create order).
- Deterministic Safety Policy Engine (`SafetyPolicy`, `OperationRisk`) classifying operations as `READ_ONLY`, `MUTATING`, or `DESTRUCTIVE`.
- OpenAPI-driven API contract testing engine (`ScenarioGenerator`, `ContractTestExecutor`, `ContractValidator`).
- Deterministic test scenario derivation (valid requests, missing parameters, missing JSON body fields, invalid enum values, missing authentication).
- Response contract validation checking status codes, Content-Type headers, and JSON schemas via `jsonschema`.
- Terminal contract test execution (`specpilot test`) and REPL slash command (`/test`) with rich summary tables and mismatch failure panels.
- Interactive human-in-the-loop approval confirmation prompts before executing side-effecting operations or mutating contract tests.
- Enforced read-only safety mode via CLI flag (`specpilot shell --read-only`, `specpilot test --read-only`) or REPL command (`/safety read-only`) blocking mutating/destructive requests prior to network execution.
- Secret-safe session history logging and verbose mode operational logging with automatic credential redaction.
- Terminal CLI inspection via `specpilot import`, `specpilot endpoints`, `specpilot tools`, `specpilot inspect <tool-name>`, `specpilot call <tool-name>`, and `specpilot test`.
- Actionable error reporting for missing files, network failures, timeouts, malformed documents, and unresolvable references.

## Interactive Shell Usage

Launch the persistent interactive shell:

```bash
specpilot shell [specification-path-or-url] [--read-only]
```

Inside the interactive shell:

```text
SpecPilot v0.6.0
Connected API: Swagger Petstore (1.0.0)
Location: ./petstore.yaml
Tools: 3 available

specpilot> /help
specpilot> /safety read-only
specpilot> /tools
specpilot> /inspect list_pets
specpilot> /call list_pets {"limit": 5}
specpilot> /test
specpilot> /use ./other_api.yaml
specpilot> /verbose on
specpilot> /history
specpilot> /exit
```

Available slash commands in `specpilot shell`:
- `/use <location>`: Load and switch to a different OpenAPI specification.
- `/api`: Display metadata and summary of the currently loaded API.
- `/tools [tag]`: List all registered MCP tools, optionally filtered by tag.
- `/inspect <tool>`: Show detailed JSON Schema input parameters and operation details for a tool.
- `/call <tool> [json]`: Execute an MCP tool with optional JSON arguments.
- `/test [tag]`: Run OpenAPI-driven contract test suite against target API.
- `/safety [read-only|interactive]`: Inspect or switch session safety execution mode.
- `/verbose [on|off]`: Toggle verbose output mode.
- `/history`: Display secret-redacted prompt command history.
- `/clear`: Clear terminal screen.
- `/help`: Display help text and available shell commands.
- `/exit`: Exit the shell session.

## API Contract Testing

SpecPilot automatically derives deterministic contract test cases directly from OpenAPI 3.x specifications:

- **Valid Request Scenarios**: Derives valid sample parameters and request bodies based on contract schemas.
- **Negative Scenarios**: Tests missing required parameters, missing JSON body fields, invalid enum values, and missing authentication headers.
- **Contract Validation**: Validates actual HTTP response status codes, content-type headers, and JSON body structure against the documented OpenAPI schema.
- **Safety Integration**: Mutating (`POST`/`PUT`/`PATCH`) and destructive (`DELETE`) test scenarios respect the active Safety Policy and require explicit permission (`--allow-mutating`) or interactive confirmation before execution.

```bash
# Run contract tests against target API base URL in read-only mode
specpilot test ./openapi.yaml --base-url https://api.example.com --read-only

# Run tests filtered by tag with JSON report export
specpilot test ./openapi.yaml --tag pets --json-output ./contract_report.json
```

## Safety Model

SpecPilot includes a built-in Safety Policy Engine to protect remote API data:

- **Read-Only (`GET`, `HEAD`, `OPTIONS`)**: Executed automatically during natural-language workflows and test runs.
- **Mutating (`POST`, `PUT`, `PATCH`)**: Requires human confirmation before execution in interactive mode.
- **Destructive (`DELETE`)**: Always requires explicit human approval before execution.
- **Read-Only Mode (`--read-only` or `/safety read-only`)**: Hard-enforces read-only execution by blocking all `POST`, `PUT`, `PATCH`, and `DELETE` requests before they reach the network executor.

## Installation

Ensure Python 3.10+ and `uv` (or `pip`) are installed.

```bash
# Editable install using uv
uv pip install -e .

# Or using standard pip
pip install -e .
```

## Configuration

SpecPilot supports LLM provider configuration via environment variables (or a `.env` file):

```bash
export SPECPILOT_LLM_API_KEY="your_api_key_here"
export SPECPILOT_LLM_BASE_URL="https://api.openai.com/v1"
export SPECPILOT_LLM_MODEL="gpt-4o-mini"
export SPECPILOT_LLM_TIMEOUT="30.0"
export SPECPILOT_LLM_MAX_STEPS="5"
```

## Authentication

SpecPilot supports target API authentication via Bearer Tokens, API Keys, and Basic Auth:

- **Bearer Token**: Set `SPECPILOT_BEARER_TOKEN="your_token"` or pass `--bearer-token`.
- **API Key**: Set `SPECPILOT_API_KEY="your_key"`, `SPECPILOT_API_KEY_NAME="X-API-Key"`, `SPECPILOT_API_KEY_IN="header"` (or `"query"`).
- **Basic Auth**: Set `SPECPILOT_BASIC_USER="user"` and `SPECPILOT_BASIC_PASS="pass"`.

All credentials are kept out of trace logs, terminal outputs, and approval prompts via automatic secret redaction.

## Observability

SpecPilot automatically captures structured execution trace logs for session commands, model interactions, MCP tool executions, HTTP requests, latencies, status codes, and approval decisions:

- **Local Trace Files**: Stored in structured JSON format under `~/.specpilot/traces/trace_<session_id>.json`.
- **Optional Langfuse Integration**: Set `LANGFUSE_PUBLIC_KEY="pk-..."`, `LANGFUSE_SECRET_KEY="sk-..."`, and optional `LANGFUSE_HOST="https://cloud.langfuse.com"` to enable cloud trace export. If unconfigured or missing, SpecPilot degrades gracefully to local tracing only.
- **Redaction Enforced**: Sensitive headers, tokens, and credentials are automatically scrubbed from trace metadata prior to persistence.



## Quick Start

```bash
# Launch interactive REPL shell
specpilot shell ./tests/fixtures/sample_3_0.yaml

# Run API contract test suite
specpilot test ./tests/fixtures/sample_3_0.yaml --read-only

# Inspect an OpenAPI specification summary
specpilot import ./tests/fixtures/sample_3_0.yaml

# List discovered endpoints and operations
specpilot endpoints ./tests/fixtures/sample_3_0.yaml

# List dynamically generated MCP tools
specpilot tools ./tests/fixtures/sample_3_0.yaml

# Inspect detailed input schema for a tool
specpilot inspect list_pets ./tests/fixtures/sample_3_0.yaml
```

## CLI Usage

```bash
# Launch interactive shell
specpilot shell ./openapi.yaml

# Run contract testing suite against target API
specpilot test ./openapi.yaml --base-url https://api.example.com --read-only

# Display help and available commands
specpilot --help

# Import local JSON or YAML specification
specpilot import ./openapi.json
specpilot import ./openapi.yaml

# Import remote OpenAPI specification over HTTP/HTTPS
specpilot import https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.json

# List endpoints table
specpilot endpoints ./openapi.yaml

# List generated MCP tools
specpilot tools ./openapi.yaml

# Inspect tool schema and metadata
specpilot inspect get_pet ./openapi.yaml

# Manually invoke an MCP tool against the target API
specpilot call list_pets ./openapi.yaml --json '{"limit": 10}'
```

## Architecture

```text
+--------------------------------------------------------+
|                     SpecPilot CLI                      |
|       (specpilot shell, test, slash & NL commands)     |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|             API Contract Testing Engine                |
|      (ScenarioGenerator, Executor, Validator)          |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|            LangGraph Stateful Agent Workflow           |
|         (SpecPilotGraph & OpenAICompatibleProvider)    |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                  Safety Policy Engine                  |
|     (OperationRisk Classification & Redactor)          |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                   MCP Tool Registry                    |
|        (Dynamic Tool Conversion & Schema Gen)          |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                    HTTP Tool Executor                  |
|    (Path Substitution, Query, Headers, Body, Secrets)  |
+--------------------------------------------------------+
```

## Supported OpenAPI Features

- OpenAPI 3.0.x and 3.1.x specifications.
- Local `$ref` pointers (e.g. `#/components/schemas/...`, `#/components/parameters/...`, `#/components/requestBodies/...`).
- Standard HTTP methods: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `HEAD`.

## Known Limitations

- Remote `$ref` resolution across external URLs is not yet supported.

## Development

Run unit tests:

```bash
uv run pytest
```

## Roadmap

- **OpenAPI Core**: OpenAPI specification loading and normalization (`v0.1.0`)
- **Dynamic MCP Tools**: Dynamic OpenAPI to MCP tool conversion and HTTP execution (`v0.2.0`)
- **Interactive CLI**: Interactive REPL shell with slash commands, autocompletion, and secret redaction (`v0.3.0`)
- **Agent Workflows**: Multi-step tool execution and LLM orchestration (`v0.4.0`)
- **Safety System**: Side-effect protection and human approval (`v0.5.0`)
- **Contract Testing**: API contract validation (`v0.6.0`)
- **Production Release**: General availability (`v1.0.0`)

## Version

Current version: `0.6.0`
