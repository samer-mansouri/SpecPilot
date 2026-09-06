# Changelog

All notable changes to SpecPilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-06

### Added
- Explicit Plan-First Execution Mode (`/plan <prompt>`) generating structured, step-by-step API execution plans with interactive developer confirmation prior to network execution.
- REPL Session State Persistence (`/save [name]` & `/load [name]`) saving and restoring active spec location, conversational memory, history, and redacted credentials under `~/.specpilot/sessions/`.
- Binary File Upload & Multipart Form Data Support in `ToolExecutor` automatically packaging file attachments for `multipart/form-data` endpoints.
- Dynamic tab autocompletion in `specpilot shell` for `/plan`, `/save`, and saved session names under `/load`.

## [1.1.0] - 2026-09-06

### Added
- Universal OpenAPI Authentication Engine (`AuthEndpointDetector`) for automatically identifying login, refresh, token, and auth endpoints across OpenAPI specifications.
- Intelligent Token Extractor (`TokenExtractor`) for extracting Bearer, OAuth2, API Key, and session tokens from nested HTTP JSON responses and headers.
- Token Lifecycle Manager (`TokenLifecycleManager`) providing token expiration detection, background re-authentication, and persistent `.env` credential state (`SPECPILOT_LOGIN_TOOL`, `SPECPILOT_LOGIN_ARGS`, `SPECPILOT_BEARER_TOKEN`).
- Transparent HTTP 401/403 auto-recovery in `ToolExecutor`, automatically re-authenticating and retrying failed API requests upon token expiry.
- Multi-turn conversational memory retention across prompts in `specpilot shell` (`SpecPilotAgent`).
- Interactive REPL slash command `/reset` to clear conversational message history.

### Fixed
- Sanitized line breaks in authorization header tokens (`AuthConfig.apply()` and `AuthManager.resolve()`), preventing `httpx.IllegalHeaderValue` errors caused by terminal line wrapping when copying raw token values.

## [1.0.2] - 2026-09-06

### Fixed
- Enforce maximum 128 tools limit when passing tools to OpenAI API (`convert_registry_to_llm_tools`) with prompt relevance scoring to prevent `array_above_max_length` HTTP 400 errors on large OpenAPI specifications.

## [1.0.1] - 2026-09-06


### Fixed
- Automatically parse and load local `.env` file variables (`SPECPILOT_LLM_API_KEY`) when initializing `LLMConfig.from_env()`.

## [1.0.0] - 2026-09-06


### Added
- Persistent user configuration profile system (`specpilot profile add/list/use/show/remove`) and global configuration inspection (`specpilot config show/path`).
- Target API authentication mechanisms supporting Bearer tokens (`SPECPILOT_BEARER_TOKEN` / `--bearer-token`), API Keys (`SPECPILOT_API_KEY` / `--api-key`), and Basic Authentication (`SPECPILOT_BASIC_USER` / `SPECPILOT_BASIC_PASS`).
- Structured execution tracing (`ExecutionTracer`) writing JSON trace logs to `~/.specpilot/traces/` and providing optional Langfuse exporter integration.
- Public developer documentation, runnable sample OpenAPI specification (`examples/petstore_sample.yaml`), and usage guides.
- Distribution packaging and console entry point build validation.

## [0.6.0] - 2026-09-06


### Added
- OpenAPI-driven deterministic scenario generator (`ScenarioGenerator`) deriving valid requests, missing required parameters, missing JSON body fields, invalid enum values, and missing authentication test cases.
- API contract test execution engine (`ContractTestExecutor`) integrated with existing HTTP execution and safety policy mechanisms (`SafetyPolicy`).
- Response contract validator (`ContractValidator`) validating HTTP response status codes, Content-Type headers, and JSON schemas via `jsonschema`.
- Terminal contract test runner CLI command (`specpilot test <location> [--tag <tag>] [--read-only] [--base-url <url>] [--json-output <path>]`).
- Interactive REPL slash command `/test [tag]` in `specpilot shell` with dynamic tag autocompletion.
- Rich formatted test summary tables, detailed scenario status breakdowns, and contract mismatch failure panels with optional JSON export.
- AI-assisted exploratory edge case scenario generator (`ExploratoryScenarioGenerator`).

## [0.5.0] - 2026-09-06

### Added
- LangGraph stateful agent workflow (`SpecPilotGraph`) supporting multi-step API execution flows and state graph orchestration.
- Deterministic Safety Policy Engine (`SafetyPolicy`, `OperationRisk`) classifying operations as `READ_ONLY` (`GET`/`HEAD`/`OPTIONS`), `MUTATING` (`POST`/`PUT`/`PATCH`), or `DESTRUCTIVE` (`DELETE`).
- Interactive human-in-the-loop approval confirmation prompt displaying colorized request details before executing side-effecting operations.
- Global `--read-only` CLI flag (`specpilot shell --read-only`) and REPL `/safety` command enforcing hard read-only safety modes that block mutating/destructive requests prior to network execution.
- Reusable `SecretRedactor` utility recursively redacting API keys, Bearer tokens, passwords, and sensitive headers from approval prompts and logs.

## [0.4.0] - 2026-09-06

### Added
- Model provider abstraction (`LLMProvider`, `OpenAICompatibleProvider`, `LLMConfig`) supporting OpenAI-compatible chat completion APIs via HTTP.
- Environment-based model configuration (`SPECPILOT_LLM_API_KEY`, `SPECPILOT_LLM_BASE_URL`, `SPECPILOT_LLM_MODEL`, `SPECPILOT_LLM_TIMEOUT`, `SPECPILOT_LLM_MAX_STEPS`) and template `.env.example`.
- MCP-to-LLM tool converter (`convert_registry_to_llm_tools`, `mcp_tool_to_llm_tool`) exposing generated API tools to the LLM as structured JSON schemas.
- Bounded agentic tool execution loop (`SpecPilotAgent`) for multi-step tool calls, argument validation, max step limits, and error handling.
- Natural language command execution directly in `specpilot shell` with verbose operational tool logging and secret redaction.

## [0.3.0] - 2026-09-06

### Added
- Interactive REPL shell (`specpilot shell`) powered by `prompt_toolkit` and `rich`.
- Active specification session state (`SessionState`) for switching specs via `/use <location>` and inspecting metadata via `/api`.
- Interactive slash commands: `/help`, `/use`, `/api`, `/tools [tag]`, `/inspect <tool>`, `/call <tool> [json]`, `/history`, `/verbose [on|off]`, `/clear`, `/exit`.
- Dynamic autocompletion (`SpecPilotCompleter`) for slash commands, tags, and registered tool names.
- Automatic secret redaction for session history ensuring API keys and tokens are never stored.
- Verbose mode toggling to output spec, tool count, and HTTP execution metrics without exposing credentials.

## [0.2.0] - 2026-09-06

### Added
- Model Context Protocol (`mcp`) SDK integration for dynamically hosting and executing API tools.
- `ToolConverter` for converting normalized OpenAPI operations into typed MCP tools with clean, deterministic snake_case naming and collision resolution.
- Automatic JSON Schema generation for tool inputs, unifying path, query, header parameters, and JSON request bodies.
- `MCPToolRegistry` for managing converted tools and binding them to MCP server instances.
- `ToolExecutor` HTTP execution engine featuring URL path parameter substitution, query formatting, header mapping, body serialization, and sensitive header redaction.
- CLI inspection & execution commands: `specpilot tools <location>`, `specpilot inspect <tool-name> <location>`, and `specpilot call <tool-name> <location> --json '{...}'`.

## [0.1.0] - 2026-09-06

### Added
- Core `src/specpilot` package structure and console script entrypoint `specpilot`.
- Specification loader supporting local JSON/YAML files and remote HTTP/HTTPS URLs with timeout handling.
- OpenAPI 3.x parser normalizing operations, paths, HTTP methods, parameters, request bodies, responses, servers, tags, and security metadata.
- JSON Pointer reference resolver (`RefResolver`) for local `$ref` pointers (e.g. `#/components/schemas/...`).
- CLI inspection commands: `specpilot import <location>` and `specpilot endpoints <location>`.
- Automated test suite covering loading, reference resolution, parsing, and CLI workflows.
