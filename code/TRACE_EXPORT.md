# Transcript and raw trace

The required conversational transcript is the append-only root `log.txt`.
Each entry records the verbatim user prompt, response summary, actions, and
authoritative runtime harness/model identity. It is a separate submission
artifact and is deliberately excluded from `code.zip`.

`agent_trace_instructions.md` additionally requests the original raw agent
trace in `agent-trace.zip`. A complete active-session trace cannot be finalized
while this chat is still writing events. After finishing and quitting the app:

1. Locate every challenge session's rollout files under the Codex session storage
   described by `agent_trace_instructions.md`, including previous work and all
   subagent reviews. Match repository/session metadata; do not copy unrelated
   conversations or settings.
2. Copy them to `agent-trace/codex/`, preserving JSONL format and relevant folders.
3. Review the staged copy and redact credentials, tokens, private information,
   and any material you cannot share. Do not copy auth files or configuration.
4. Create `agent-trace.zip` and inspect its contents before uploading.

No raw trace archive is claimed to be finalized by the running audit pipeline.
