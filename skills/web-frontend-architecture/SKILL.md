---
name: web-frontend-architecture
description: Monorepo-wide stack, state-management, import-boundary, naming, and tooling conventions for the `web` npm-workspaces repo (packages/components, external, fieldfocus, first-draft, gmi, platform, product-manager, pso, qa, utils). Covers React 18.3/TypeScript 7/Vite 8, Redux Toolkit as the only external state library (with the real redux-act reducer pattern, not createSlice), the `@web/<package>/src/...` import-alias boundary, the component/hook/util promotion ladder mapped to real folder names, and that oxlint+oxfmt (not ESLint/Prettier) are the enforced lint/format tools. This is the monorepo-wide companion to `one-solution-frontend-architecture`, which remains the authority on the target features/hooks/services/domain/api layering for One Solution (first-draft) feature work — load both when doing feature work in first-draft; load this one alone for anything touching platform/utils/components, cross-package conventions, state, or tooling in any package. Use whenever adding a component/hook/page, deciding where code or state belongs, wiring a new Redux module, reviewing a frontend PR, or asking "is this the right place for this file."
---

# Web Monorepo Frontend Architecture (`web` repo)

## Verified state — checked 2026-09-17 against `develop`, cross-checked against the cached `origin/one-solution` branch (`git ls-tree`, no checkout)

- **No package in this repo — including `first-draft` — currently has a `features/`, `services/`,
  `domain/`, or top-level `hooks/` directory.** `first-draft/src` is flat:
  `components/`, `contexts/`, `helpers/`, `pages/`, `static/`, `utils/`. `qa/src` is the same
  shape (`components/`, `pages/`, `model/`, `utils/`, `appContext/`). This was re-verified
  directly (not assumed) after an earlier draft of this task incorrectly took "first-draft
  already follows feature-driven layering" as given — it doesn't, on `develop` or on the last
  fetched state of `one-solution`. The `features/hooks/services/domain/api/types/utils/stores`
  layout is the **target** described in the companion `one-solution-frontend-architecture` skill
  (sourced from an internal doc), not something already built — see that skill for the full
  target shape and layer rules; this skill treats it as the direction new first-draft (and,
  where practical, `qa`) feature work should move toward, not a retrofit mandate.
- **`@json-render` is not used anywhere in this repo** — not a dependency in any `package.json`,
  no imports. Don't document or assume usage patterns for it; if it's genuinely being added,
  that's a new-dependency decision (see `deps-doctor` skill), not an existing convention.
- **The real Redux reducer pattern is `redux-act`'s `createReducer` + hand-rolled action-type
  factories, not `@reduxjs/toolkit`'s `createSlice`.** `createSlice`/`createApi` appear nowhere
  in the codebase (checked). `@reduxjs/toolkit` is genuinely used, but only for `configureStore`
  (and `combineReducers` in some modules) — store wiring, not reducer authoring. See the State
  section below for the exact pattern, verified against `packages/utils/src/{store,redux}.ts` and
  `packages/platform/src/modules/{auth,users}/*.ts`.
- **`AGENTS.md` (repo root) explicitly scopes Redux to "existing components and platform package
  changes"** and says "all newer features to use react context where needed." So Redux Toolkit
  is correctly the repo's *only third-party state-management library* (no Zustand/MobX/Jotai/
  TanStack Query/SWR anywhere — confirmed), but it is not the default reach for new feature-local
  state — `useState`/Context come first. See State section for how this reconciles.
- **`oxlint` + `oxfmt` are the real lint/format tools**, confirmed directly in root
  `package.json`'s `lint-staged` config (`oxlint --fix ...` / `oxfmt` / `stylelint --fix`) and
  `.oxlintrc.json`/`.oxfmtrc.json` at repo root. `AGENTS.md`'s own prose says "prettier" in one
  place — that's stale relative to the actual lint-staged config; there is no `.eslintrc`
  anywhere and none should be added.
- **The `I`-prefix interface convention is a minority pattern here** (~60 `interface IXxx`
  declarations vs ~592 plain `interface Xxx`, checked via grep) — don't impose it as a house
  rule; it isn't one in this codebase, even though it's common in other React style guides.
- Stack versions confirmed in root `package.json`: `react@^18.3.1`, `typescript@^7.0.2`,
  `vite@^8.1.5`, `react-router-dom@^6.30.3`, `redux@4.2.1`, `@reduxjs/toolkit@^2.12.0`,
  `redux-act@1.8.0`, `jest@^30.4.2`, `@sentry/react@^10.68.0`.

## Relationship to `one-solution-frontend-architecture`

That skill is the **authority on the target feature-layering** for the One Solution / first-draft
product: `features/{feature}/{components,hooks,services,domain,api,types,utils}/`, its dependency
direction (`Pages → Features → Hooks → Services → Domain + API → Backend`), and its promotion
rule ("start feature-specific; promote to `shared/` only when ≥2 features need it"). Load it for
any first-draft feature work.

This skill is the **monorepo-wide companion**: the stack, state-management reality, cross-package
import boundary, tooling, and naming conventions that apply across *all* packages
(`components/external/fieldfocus/first-draft/gmi/platform/product-manager/pso/qa/utils`), not
just first-draft. Where the two overlap (e.g. import boundaries inside first-draft's future
`features/` folders), the narrower skill's rule wins — this skill fills in what it doesn't cover:
Redux's real shape, the `useFetch` data layer, cross-*package* (not cross-feature) boundaries, and
tooling.

## Package map (`packages/*`, npm workspaces)

| Package | Role | Structure today |
|---|---|---|
| `first-draft` | Product: First Draft / One Solution FDM | Flat (`components/pages/contexts/utils/helpers`) — **target**: feature-layered, see companion skill |
| `qa` | Product: Q&A/DORA, actively developed | Flat (`components/pages/model/utils/appContext`) — apply first-draft-style layering to *new* features here where practical, same as first-draft |
| `fieldfocus`, `gmi` | Products, **maintenance-only** (AGENTS.md) | Flat legacy layout — don't restructure; don't even bring these up to design-system parity per AGENTS.md's own guidance |
| `platform` | Core shell: auth, routing, product registry, Redux store wiring | `containers/layouts/modules/pages/routes/standalone` |
| `utils` | Shared hooks, config system, contexts, the Redux store itself, `useFetch` | `hooks/modules/constants/styles` |
| `components` | Shared UI component library (legacy, pre-design-system) | Flat, has a real curated barrel at `src/index.ts` |
| `product-manager`, `pso`, `external` | Smaller flat products/utilities | Flat |

## Where new feature code belongs

- **first-draft**: new or refactored features target the `features/{feature}/` layering from
  `one-solution-frontend-architecture` — components/hooks/services/domain/api/types/utils under
  one feature folder, one curated `index.ts` barrel. This is genuinely new; don't treat any
  existing first-draft folder as an example to copy from.
- **qa**: same target shape for new feature work, applied without forcing a disruptive rewrite of
  existing `pages/`/`components/`/`model/` code — AGENTS.md marks qa as actively developed and
  design-system-forward, unlike fieldfocus/gmi.
- **fieldfocus, gmi**: maintenance-only. Leave the flat layout as-is; don't migrate these to
  feature-layering or the design system unless separately asked.
- **platform, utils, components**: these are infrastructure/shared packages, not product feature
  surfaces — they don't get a `features/` folder. `platform` stays organized by
  `modules/<concern>` (auth, users, invites, settings), `utils` by technical concern
  (`hooks/`, `config/`, `styles/`), `components` by one folder per shared component.
  `product-manager`/`pso`/`external`: small enough today that flat is fine; apply the same "new
  work moves toward feature-layering, don't force a rewrite" logic if they grow.

## State: split by origin — Redux Toolkit is the only external state library, but it isn't the default

No Zustand, MobX, Jotai, TanStack Query, or SWR exist anywhere in this repo — Redux
(`redux` + `redux-act` + `@reduxjs/toolkit` for store setup) is genuinely the only third-party
state tool, so don't introduce or suggest an alternative. But "only state library" doesn't mean
"reach for it by default" — `AGENTS.md` is explicit that Redux is for *existing* components and
*platform*-package changes, and new features should prefer React's own primitives first:

| State kind | Lives in | Notes |
|---|---|---|
| Local component state | `useState` | Default for anything not shared outside one component |
| Shared across a component tree within one feature/page | React Context | AGENTS.md: "all newer features to use react context where needed" — this is the target for new first-draft/qa feature state, not Redux |
| Cross-cutting / global (auth, current user, notifications) or existing platform-package state | Redux (`redux-act`) | Legacy-maintained, scoped to `platform` per AGENTS.md — extend existing modules or add a new one only when the state is genuinely global, not feature-local |
| Server data | `useFetch` hook (`@web/utils/src/hooks`) | Not RTK Query — see below |

### The real Redux pattern (verified — do not use `createSlice`)

`createSlice`/`createApi` are not used anywhere in this repo. A new Redux module should match the
existing shape exactly:

1. Action-type factories from `@web/utils/src/redux` — `requestAction`, `successAction`,
   `failureAction`, `cleanupAction`, `replaceAction`, `destroyAction`, `cancelAction`, scoped by a
   `MODULE_NAME` string constant (e.g. `'AUTH/AUTHENTICATION'`).
2. A reducer built with `redux-act`'s `createReducer({ [ACTION]: handler, ... }, initialState)`.
3. One folder per concern under `packages/platform/src/modules/<feature>/` (e.g. `auth/`,
   `users/`), combined with `combineReducers` in that module's `index.ts`, and folded into the
   single store's reducer map in `packages/utils/src/store.ts` via `@reduxjs/toolkit`'s
   `configureStore` — this `configureStore` call is RTK's actual role here: store assembly, not
   slice authoring.
4. Access via the typed hooks already provided — `useAppDispatch`/`useAppSelector`/`useAppStore`
   from `@web/utils/src/hooks` — never `useDispatch`/`useSelector` directly from `react-redux`.

### Server data: `useFetch`, not RTK Query

`useFetch` (`@web/utils/src/hooks`, implementation at
`packages/utils/src/hooks/useFetch/useFetch.tsx`) wraps native `fetch` with product-context URL
prefixing, caching, cancellation, and Sentry error logging. Build feature-specific data hooks on
top of it (e.g. first-draft's `useDataPolling` wraps `useFetch` for polling) rather than calling
`useFetch` or raw `fetch` directly from a component. There is no RTK Query `createApi` usage to
model against — don't introduce one without a deliberate decision to adopt it repo-wide.

## Import boundaries

- **Cross-package** (already established, hard rule per AGENTS.md): `@web/<package>/src/...`
  aliased imports only — package name matches the npm workspace name (`@web/first-draft`,
  `@web/platform`, `@web/utils`, `@web/components`, ...). Never a relative import that crosses a
  package boundary.
- `@web/components` additionally exposes a curated root barrel
  (`export { default as X } from './X'` in `packages/components/src/index.ts`) for shared legacy
  UI — prefer importing from `@web/components` directly over deep-pathing into
  `@web/components/src/X` when the component is exported from the barrel.
- **Cross-feature, within a package** (new — applies once a package adopts the `features/`
  layering): each feature exposes exactly one `index.ts` barrel; other features and pages import
  only from `@web/first-draft/src/features/{feature}` (or the package's own alias), never from a
  feature's internal `components/hooks/services/domain/api` paths directly. This mirrors the
  dependency-direction rule in `one-solution-frontend-architecture` and is the piece that skill
  doesn't spell out explicitly — treat it as this skill's addition, not a contradiction.

## Component / hook / util promotion ladder (mapped to real folder names)

| Used by | Lives in | Imported as |
|---|---|---|
| Only one page | `pages/{Page}/components/` (already the real pattern — e.g. `pages/Project/components/Sections/components/Config/components/DraftSections/`) | relative, within the page |
| 2+ pages in one feature (first-draft target) | `features/{feature}/components/` — today, before the layering exists: package-root `components/` | `@web/<package>/src/features/{feature}` once barrels exist |
| 2+ product packages | `packages/components/src/` | `@web/components` |
| Needs a real design-system token/component, not just JS reuse | `@ets/design-system` | `import { X } from '@ets/design-system'` |

Same ladder for hooks and utils: start local to the page/feature, promote to package `utils/`
only on a second consumer, promote to `@web/utils` only when 2+ packages need it. Don't pre-place
"because it might be reused."

## Naming conventions (from actual usage)

- **Components**: PascalCase directory with `index.tsx` inside (`ErrorState/index.tsx`,
  `GreenCard/index.tsx`) — not a bare `ComponentName.tsx` file.
- **Hooks**: camelCase filename matching the hook name, colocated test —
  `useDataPolling.tsx` / `useDataPolling.test.tsx`.
- **Styles**: CSS Modules only, `index.module.scss` (or `{Name}.module.scss`) colocated with its
  component; stylelint-enforced (`.stylelintrc.js`). No inline `style={{...}}` for anything
  beyond a truly one-off dynamic value.
- **Tests**: colocated as `__tests__/<file>.test.tsx` or `<file>.test.tsx` next to the source
  (AGENTS.md).
- **Interfaces/types**: plain PascalCase (`AuthState`, `UserSelfResponse`) — do **not** impose an
  `I`-prefix convention; it's present but a clear minority in this codebase.
- **Redux modules**: `MODULE_NAME` string constant + the standard `REQUEST/SUCCESS/FAILURE/
  CLEANUP/REPLACE/CANCEL` actions via the factories in `@web/utils/src/redux`.
- **Packages**: `@web/<package>`, matching the directory name under `packages/`.

## Tooling: oxlint + oxfmt — not ESLint/Prettier

- `.oxlintrc.json` and `.oxfmtrc.json` at repo root; `lint-staged` (root `package.json`) runs
  `oxlint --fix --fix-suggestions` on `*.{js,jsx,ts,tsx}`, `oxfmt` on
  `*.{js,jsx,ts,tsx,md,html,json}`, and `stylelint --fix` on `*.{css,scss}`; `.husky/pre-commit`
  just calls `npx lint-staged`.
- Don't propose adding or configuring ESLint or Prettier — there's no `.eslintrc` anywhere in the
  repo and none should be introduced. If `AGENTS.md` prose says "prettier" anywhere, that's stale
  relative to the actual lint-staged config; trust `package.json`, not the prose.
- Verify with `npm run lint` (oxlint + stylelint, autofix), `npm test` (Jest, silent mode),
  `npm run ts-coverage` — same commands already in the house verification list for this repo.

## Styling / UI libraries

- SCSS + CSS Modules is the only styling approach; Bootstrap SCSS underlies some legacy
  components.
- `@ets/design-system` is the preferred UI library for **new** screens/features in the QA and
  First Draft packages specifically (AGENTS.md) — other packages still use legacy
  `@web/components`/FontAwesome Pro icons; don't mix design-system and legacy components within
  one feature.
- `@dnd-kit` for drag-and-drop — real usage confirmed in first-draft's section-ordering UI
  (`pages/Project/components/Sections/components/Config/components/DraftSections/`).
- TipTap for rich text — real usage confirmed in first-draft's
  `pages/Project/components/Sections/components/ReviewAndEdit/components/RichTextEditor/`.
- FontAwesome Pro ships via the legacy `@web/components/src/Icon` system, which coexists with
  `@ets/design-system`'s own `Icon` — pick one per feature, don't mix.

## i18n

`i18next`, namespaced `t('package:path.to.key', { defaultValue: '...' })` — `defaultValue` is
required for string extraction. Run `npm run i18next` before committing new strings.

## Testing

Jest 30 + React Testing Library, jsdom environment, Babel transform. Tests colocate per the
naming section above.

## Review checklist

- [ ] New feature work in first-draft/qa targets `features/{feature}/{components,hooks,services,
      domain,api,types,utils}/` with one curated `index.ts` barrel (see
      `one-solution-frontend-architecture`) — not forced onto fieldfocus/gmi (maintenance-only)
      or onto a small passthrough change that doesn't need the full shape
- [ ] No new Redux module for state that's local to one feature or one page — `useState`/Context
      first; Redux only for genuinely cross-cutting/global state, using the `redux-act` +
      action-factory pattern (never `createSlice`, which isn't used anywhere in this repo)
- [ ] No Zustand/MobX/Jotai/TanStack Query/SWR introduced — Redux Toolkit (for store setup) +
      `redux-act` (for reducers) + `useFetch` (for server data) are the only state/data
      primitives here
- [ ] Cross-package imports use `@web/<package>/src/...`, never a relative path across a package
      boundary
- [ ] Cross-feature access (once a package's `features/` folder exists) goes through that
      feature's `index.ts` barrel, not a deep path into its internals
- [ ] A shared component/hook/util is promoted no further than its actual consumer count
      requires: page → package `components/` (or `features/{feature}/components/`) →
      `@web/components` → `@ets/design-system`
- [ ] Styling is CSS Modules SCSS only, no inline `style={{...}}`, stylelint passes
- [ ] i18n strings include `defaultValue` and use the `package:path` namespace
- [ ] No ESLint/Prettier config introduced or suggested — oxlint/oxfmt (`npm run lint`) are the
      enforced tools
- [ ] `@json-render` isn't referenced as if it's an existing pattern — it has zero usage in this
      repo as of this check

## What NOT to do

- Don't restructure fieldfocus/gmi toward feature-layering or the design system — AGENTS.md marks
  them maintenance-only.
- Don't treat first-draft's current flat layout (`components/pages/contexts/utils/helpers`) as if
  it already were feature-layered — it isn't, on `develop` or the last-fetched `one-solution`
  state. Say so plainly if asked to "follow the existing first-draft pattern" for layering; there
  isn't one yet.
- Don't introduce `createSlice`/`createApi`-based Redux modules — every existing module uses
  `redux-act` + the action-factory helpers in `@web/utils/src/redux`; a slice-based module would
  be inconsistent with all of them.
- Don't reach for Redux for feature-local or single-page state — AGENTS.md scopes it to "existing
  components and platform package changes."
- Don't impose an `I`-prefix interface rule — it's a minority pattern here, not a house
  convention, even though it's common in other React style guides (including the public
  reference skill this was adapted from).
- Don't document or assume `@json-render` usage patterns — there's nothing real to model them on.
- Don't propose ESLint or Prettier configuration — this repo deliberately uses oxlint/oxfmt.
