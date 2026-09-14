# JARVIS NEO Agent Core

This branch introduces the first independent agent engine. It is deliberately separated from `assistant.py` so the existing HUD can keep working while the new architecture is validated.

## Execution model

`goal -> decision -> tool -> observation -> verification -> next decision -> result`

The LLM is a planner. It never executes Python directly. Every action goes through `ToolRegistry`, then `PermissionPolicy`.

## Permission modes

- **1 / Prudent**: routine operations require approval.
- **2 / Autonomous**: normal operations are automatic; sensitive operations can pause the task.
- **3 / Unrestricted**: routine confirmation prompts are disabled so long-running missions can continue while the user is away.

Mode 3 is a user setting, not an instruction emitted by the LLM.

## Persistent missions

`TaskManager` stores each task as JSON under `.jarvis/tasks/`. A task records:

- goal
- current step
- status
- context
- tool results
- errors
- event history

This lets JARVIS resume work after a restart instead of forgetting everything.

## Current built-in tools

- `filesystem.list`
- `filesystem.read`
- `filesystem.write`
- `filesystem.search`
- `filesystem.delete`
- `system.run_command`

The registry is intentionally extensible. Browser, GUI, vision, Git, package management, web APIs, mobile and plugin tools can be added without changing the agent loop.

## Local model adapter

`neo_agent.ollama.OllamaAdapter` talks to the local Ollama HTTP API and asks the model for one structured JSON decision at a time.

## Integration strategy

Do not replace `assistant.py` wholesale yet. First validate the core independently, then migrate existing capabilities into registered tools, then connect the HUD to task events and controls.
