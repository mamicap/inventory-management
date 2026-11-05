# CLAUDE.md - Server

This file provides guidance to Claude Code (claude.ai/code) when working with the FastAPI backend.

## Commands

```bash
uv run python main.py                    # http://localhost:8001, docs at /docs
cd ../tests && uv run pytest backend/ -v # tests import main.app directly; no server needed
```

Dependencies are in `pyproject.toml` (`uv sync`). `generate_data.py` (run from `server/`) regenerates only `data/orders.json`, with random values.

## Architecture

- `mock_data.py` loads every file in `data/*.json` into module-level lists at import time. There is no database and nothing persists across restarts.
- `main.py` holds the Pydantic models, the shared filter helpers (`apply_filters`, `filter_by_month`) and every route. Routes use `response_model` where a model exists.
- CORS allows all origins and there is no auth - local demo only.

## Conventions

- Filter params are optional query params. The value `'all'` means "no filter", and string matching on category is case-insensitive.
- `month` accepts a direct month (`2025-01`) or a quarter key from `QUARTER_MAP` (`Q1-2025` to `Q4-2025`). It does a substring match on `order_date`, so handle missing dates without raising.
- Filter on copies of the data, never mutate the module-level lists.
- Not-found returns `HTTPException(404, ...)`.
- Filter param names must stay consistent across endpoints (`warehouse`, `category`, `status`, `month`) because `client/src/api.js` sends them by name.

## When changing data

- Update the Pydantic models in `main.py` whenever the JSON structure changes (mark a field `Optional` before removing it), and update the affected tests.
- Keep SKUs in orders valid against `inventory.json`, and keep category names and date formats consistent across data files.
- Restart the server to reload data.

## Adding an endpoint

Define the model, add the route in `main.py`, then add tests in `tests/backend/` (use the `backend-api-test` skill).
