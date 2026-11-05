# CLAUDE.md

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient (run commands are under Commands below)

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)
- Both servers are defined in `.mcp.json` and launched via `npx`, so Node/npx must be on PATH. The GitHub server also needs `GITHUB_PERSONAL_ACCESS_TOKEN` in the environment. If they fail to connect, check those two first.

## Stack
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Prerequisites
- Python >=3.11 with `uv`; Node `^20.19.0 || >=22.12.0` (required by Vite 8)
- On Windows, `scripts/*.sh` need Git Bash. A shell opened before installing Node/uv may not have `node`, `npm` or `uv` on PATH - open a new terminal.

## Commands

```bash
# Both servers (bash only)
./scripts/start.sh   # ./scripts/stop.sh to stop

# Backend (http://localhost:8001, docs at /docs)
cd server
uv run python main.py

# Frontend (http://localhost:3000)
cd client
npm install && npm run dev
npm run build        # output in client/dist/

# Backend tests (pytest + FastAPI TestClient; no running server needed)
cd tests
uv run pytest -v
uv run pytest backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory -v   # single test
```

There is no linter and no frontend test setup. `tests/backend/conftest.py` adds `server/` to `sys.path` and imports `main.app` directly.

## Key Patterns

**Filter System**: 4 filters (Time Period, Warehouse, Category, Order Status) apply to all data via query params
**Data Flow**: Vue filters → `client/src/api.js` → FastAPI → In-memory filtering → Pydantic validation → Computed properties
**Reactivity**: Raw data in refs (`allOrders`, `inventoryItems`), derived data in computed properties

**Frontend architecture**
- `client/src/api.js` hardcodes `http://localhost:8001/api` and omits any filter whose value is `'all'`.
- Filter state lives in module-level refs in `composables/useFilters.js` (singleton shared by all views). `getCurrentFilters()` maps the UI names to API params (`selectedLocation` → `warehouse`, `selectedPeriod` → `month`).
- `composables/useAuth.js` and `useI18n.js` follow the same composable pattern; locales are in `client/src/locales/` (en, ja).
- Pages are `views/*.vue`; drill-downs are `components/*DetailModal.vue`.
- `views/Restocking.vue` computes recommendations client-side: join demand forecasts to inventory on SKU, shortfall = forecast minus stock, then fill the budget greedily from the largest shortfall. Placed orders show in the "Submitted Orders" card in `views/Orders.vue`.

**Backend architecture**
- `server/mock_data.py` loads every `server/data/*.json` file into module-level lists at import time; `server/main.py` holds the Pydantic models, shared filter helpers (`apply_filters`, `filter_by_month`) and all routes. Nothing persists across restarts.

## API Endpoints
- `GET /api/inventory` - Filters: warehouse, category
- `GET /api/orders` - Filters: warehouse, category, status, month
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters
- `GET /api/spending/*` - Summary, monthly, categories, transactions
- `GET /api/restocking-orders`, `POST /api/restocking-orders` - Submitted restocking orders (the only write endpoint). The server recomputes unit costs, totals and lead time (max of per-category `LEAD_TIME_DAYS`) from inventory and rejects orders over budget. Orders live in the module-level `restocking_orders` list in `main.py`, so they reset on restart.

## Common Issues
1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months

## File Locations
- Views: `client/src/views/*.vue`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`

## Design System
- Colors: Slate/gray (#0f172a, #64748b, #e2e8f0)
- Status: green/blue/yellow/red
- Charts: Custom SVG, CSS Grid for layouts
- No emojis in UI
