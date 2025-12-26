---
applyTo: '**'
---

# Project overview
This repo extracts occupations and skills from World Bank PAD PDFs.
Pipeline: PDF -> Markdown -> LLM extraction -> structured outputs (JSON/CSV) -> visualization/app.

## Workflow
- Before edits: briefly restate the goal and the plan in 3–6 bullets.
- Make changes in small steps. After each step: summarize changed files and how to verify.
- Prefer minimal diffs. Do not reformat unrelated code.

## Notebook-first development
- Prototype and validate logic in `notebooks/` first (quick experiments, inspections).
- After the approach is validated, implement the reusable version in `src/` as functions/modules.
- `src/` should be importable and testable; notebooks should call into `src/` (not duplicate logic long-term).
- If notebook code is promoted to `src/`, add/adjust tests (or at minimum a small smoke test).

## Repo conventions
- Production code lives in `src/`.
- Notebooks are exploratory; keep outputs small and avoid committing large generated artifacts.
- Ask before adding new dependencies.

## Project commands
- Install: `uv sync` and be sure to update notes.md if needed.
- Lint: `ruff check .`
- Format: `ruff format .`
- Tests: `pytest -q`

## Python conventions
- Target Python 3.11.
- Prefer type hints. Avoid new dependencies unless necessary.

## Safety rails
- Do not commit secrets.
- If uncertain, ask for clarification or propose 2 options and recommend one.