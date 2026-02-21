# Task 12: Create Standard Phase Template

## Context

This is **Maintenance Mechanism 3**: Create a standard template for future phases where the final task is always "Update documentation." This ensures every phase's `000-start.md` includes doc maintenance by default.

## Action

Create `docs/cursor-prompts/PHASE_TEMPLATE.md` with the following content:

```markdown
# Phase Template

Use this template when creating a new phase directory. Copy and customize.

---

## Directory Setup

```bash
mkdir -p docs/cursor-prompts/phaseNNN-description
```

## 000-start.md Template

```markdown
# Phase NNN — Title

## Goal

One paragraph describing what this phase accomplishes.

## Current State (problem)

What's wrong or missing today.

## Target State

What the codebase looks like after this phase.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-first-task.md` | Description | — |
| 2 | `002-second-task.md` | Description | Step 1 |
| ... | ... | ... | ... |
| N | `00N-update-documentation.md` | Update affected docs | Steps 1-(N-1) |

## Verification

```bash
# Commands to verify the phase is complete
```

## Documentation Impact

List docs affected by this phase:
- `docs/[section]/[file].md` — [what changes]
```

## Task Prompt Template

```markdown
# Task N: [Title]

## Context

Why this task exists and what problem it solves.

## Actions

Step-by-step instructions for the executing AI.

## Verification

How to confirm the task is complete.
```

## Final Task Template (ALWAYS include as last task)

```markdown
# Task N: Update Documentation

## Context

Phase NNN changed [summary of what changed]. The following docs need updating.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/[section]/[file].md` | [description of update needed] |

## For Each File

1. Read the current content
2. Update the relevant sections to reflect this phase's changes
3. Update the YAML frontmatter:
   - Set `last-verified` to today's date
   - Add phase NNN to the `phases` array
   - Add/update `sources` if new source files are relevant
4. Verify no stale information remains

## If No Docs Are Affected

If this phase truly has no documentation impact (e.g., pure test fixes, internal refactoring with no behavior change), document that explicitly:

"No documentation updates needed — this phase [reason]."
```

## Naming Convention

- Directory: `phaseNNN-short-description` (no hyphen between "phase" and number)
- Files: `000-start.md`, `001-first-task.md`, `002-second-task.md`, ...
- Always include `000-start.md` as entry point
- Always include a documentation update as the final task
```

## Why

This template:
1. Standardizes phase structure across all future phases
2. Makes the documentation update task impossible to forget — it's in the template
3. Includes the freshness metadata update instructions so executing AI knows exactly what to do
4. Reduces cognitive load when creating new phases — copy template, customize, go
