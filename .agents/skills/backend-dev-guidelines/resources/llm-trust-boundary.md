# LLM And Trust Boundary

Load this for LLM calls, prompts, tool output, uploaded files, parsed documents, model-generated JSON, embeddings, or external untrusted metadata.

## Treat As Untrusted

- User input
- Uploaded file names/content/metadata
- LLM responses, tool calls, structured output, citations, and extracted fields
- Third-party SDK payloads

## Validation

- Validate external/LLM output at the adapter or application boundary with Pydantic or explicit checks.
- Do not insert raw model output into domain entities without shape/range validation.
- Use allowlists for enum/status/type fields.
- Enforce size limits for prompts, file content, metadata, and stored JSON.

## Grounding And Provenance

- Store provenance when business behavior depends on generated content.
- Keep raw provider response only if there is a clear debugging/audit need and it is safe to store.
- Avoid logging full prompts, documents, or generated sensitive content.

## Failure Handling

- Distinguish provider unavailable, invalid provider output, unsafe/untrusted content, and business validation failure.
- Invalid LLM output should be an expected failure path with retry/fallback only when safe.

## Tests

- Valid structured output.
- Missing/wrong type/extra invalid enum field.
- Oversized or unsafe metadata.
- Provider timeout/error.

## Completion Check

- Untrusted output is validated before domain/persistence.
- Prompt/output logging is safe.
- Invalid output does not silently create bad data.
- External provider details are hidden behind an application port.
