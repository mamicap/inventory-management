# CLAUDE.md - Client

This file provides guidance to Claude Code (claude.ai/code) when working with the Vue 3 frontend.

## Commands

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # output in dist/
```

No linter or test runner is configured. `.vue` files must be created or significantly modified via the `vue-expert` subagent (see root `CLAUDE.md`).

## Conventions

- Components use `export default { setup() { ... } }` with Composition API (`ref`, `computed`, `watch`, `onMounted`) and `<style scoped>`. Do not mix in Options API data/methods.
- Raw API data goes in refs; anything derived goes in `computed`. Never mutate props - emit events to the parent.
- Shared state lives in singleton composables (module-level refs, see `composables/useFilters.js`), not in components.
- All HTTP calls go through `src/api.js`; the base URL is hardcoded to `http://localhost:8001/api`. Filter values of `'all'` are dropped from the query string there.
- Load data with `loading` / `error` refs, `try/catch/finally`, and render all three states in the template.
- UI strings go through `useI18n` (`src/locales/en.js`, `ja.js`); add keys to both locales. Not every view uses it yet (`Backlog.vue` and `Reports.vue` don't).
- Currency formatting helpers are in `src/utils/currency.js`.

## Pitfalls

- Use unique keys in `v-for` (`sku`, `month`, `id`), never the index.
- Validate dates (`isNaN(date.getTime())`) before calling `.getMonth()` and similar.
- Inventory endpoints do not accept a `month` filter - don't pass the period filter to them.
- Charts are custom SVG (no chart library); keep chart data in computed properties and handle empty data.
