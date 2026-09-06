# SpecPilot Usage Examples

This directory contains sample OpenAPI specifications and executable usage examples for SpecPilot.

## Example 1: OpenAPI to MCP Tool Execution

```bash
# 1. Inspect generated MCP tools
specpilot tools ./examples/petstore_sample.yaml

# 2. Call an endpoint tool directly
specpilot call findPetsByStatus ./examples/petstore_sample.yaml --json '{"status": "available"}'
```

Flow: `OpenAPI spec -> generated MCP tools -> natural-language request -> tool calling -> API result`

## Example 2: Multi-Step Workflow with Safety & Mutation Approval

```bash
# Launch interactive REPL shell in interactive safety mode
specpilot shell ./examples/petstore_sample.yaml
```

```text
specpilot> Find all available pets, select the first pet name, and add a new pet with that category.
[Safety Policy] POST /pet requires approval (MUTATING operation).
[Approval Prompt] Execute POST /pet with arguments {"name": "Buddy", "photoUrls": ["http://example.com/photo.jpg"]}? [y/N]: y
[Executed] POST /pet -> 200 OK
```

Flow: `multi-step workflow -> approval -> mutation -> verification`

## Example 3: API Contract Testing & Mismatch Report

```bash
# Run contract test suite in read-only safety mode
specpilot test ./examples/petstore_sample.yaml --base-url https://petstore.swagger.io/v2 --read-only
```

Flow: `contract test -> mismatch report`
