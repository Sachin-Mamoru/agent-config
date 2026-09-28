---
name: one-solution-frontend-architecture
description: >
  Feature-driven frontend architecture (components/hooks/services/domain/api/types/utils/stores)
  for the One Solution fdm frontend in the `web` monorepo. Source: internal doc "Frontend
  Architecture: Organizing Features, Components, and Services for a Scalable Application" by
  Mohamed Ruzni (2026-09-14). Use for ANY frontend change on the One Solution fdm product — new
  components, hooks, API calls, business rules, or deciding where a piece of code belongs.
---

# One Solution — FDM Frontend Architecture (web repo)

## Verified state (checked 2026-09-14, against `web` repo)

- No package under `web/packages/*` currently uses this layered structure — `features/`,
  `domain/`, `services/` folders don't exist anywhere in the repo today. Existing products
  (`first-draft`, `qa`, `fieldfocus`, `gmi`) use a flatter `components/pages/utils/helpers/model`
  layout (see `web/AGENTS.md`).
- **This is net-new guidance scoped to One Solution frontend work, not a retrofit mandate.**
  Don't restructure fieldfocus/gmi (maintenance-only per `AGENTS.md`)/qa/first-draft to match
  this unless separately asked.
- This governs *internal layering within* the One Solution package — it sits underneath, not
  instead of, `web/AGENTS.md`'s monorepo-level conventions: `@web/<package>/src/...` import
  aliases (never relative imports across packages), CSS Modules (`*.module.scss`), i18n
  namespacing (`t('package:path', { defaultValue })`), `@ets/design-system` for new screens,
  and product registration via `config.jsx` exporting `NAME`.

## Core principle

Organize by feature/business-domain, not by technical layer. Every piece of code has exactly one
job — ask **"what is this code responsible for?"** before placing it:

| Layer | Answers | Contains |
|---|---|---|
| Page | "What's on this screen?" | Composes features together, no business logic |
| Component | "What does the user see?" | Rendering, props, events, calls hooks — never fetch/business rules directly |
| Hook | "How does this behave in React?" | `useState`/`useEffect`, wires UI to a service |
| Service | "What should the app do?" | Application workflow/action (multi-step: check → call → update → return) |
| Domain | "Is this allowed?" | Pure business-rule functions, no API calls |
| API | "How do I talk to the backend?" | HTTP only — no permission/business logic |
| Types | "What does this look like?" | Data shape only, no behavior |
| Utils | "How do I format/transform this?" | Small, generic, reusable — no business meaning |
| Store | Shared client state used by multiple unrelated components | State only — not a dumping ground for API/rules/formatting |

**Dependency direction is one-way**: `Pages → Features → Hooks → Services → (Domain + API) →
Backend`. A component must never call `fetch`/an API client or embed business rules inline —
always through a hook → service.

## Directory structure (scaffold this for the One Solution package)

```
src/
├── components/            # globally reusable UI (Button, Modal, Spinner...) — no business logic
├── pages/                 # page-level composition only
├── features/
│   └── <feature>/
│       ├── components/    # feature-specific UI, allowed to know the feature's data shape
│       ├── hooks/
│       ├── services/      # workflows: createX(), deleteX(), generateX()
│       ├── domain/        # business rules: canDeleteX(x), canChangeLanguage(project)
│       ├── api/            # HTTP only
│       ├── types/
│       └── utils/
├── shared/                 # hooks/services/domain/types genuinely used by 2+ features
├── api/
│   ├── client.ts
│   └── okra_kit/            # queryBuilder.ts, types.ts, operators.ts — shared backend query building
├── stores/                  # shared client-side state
├── utils/                   # generic, feature-agnostic helpers
```

## Worked example: where does `deleteProject(id)` belong?

- Just `DELETE /projects/:id`, nothing else → **API** layer.
- Check-if-allowed → delete → clean up local state → return result → **Service**.
- "Can a project be deleted when it has generated drafts?" → **Domain**.
- The component only ever calls `await deleteProject(project.id)` — it never knows which of the
  above actually happens underneath.

## Rules to actually enforce in review

1. **API layer never decides permission/business rules.** No "should this be allowed" logic
   inside `api/` — that's a domain concern leaking into the transport layer.
2. **Services never contain JSX or pure formatting.** UI belongs in components, formatting in
   utils; a service is a workflow (multi-step application action), not a dumping ground.
3. **Domain functions are pure.** Take data in, return allowed/not-allowed (or a derived value);
   no API calls, no side effects inside `domain/`.
4. **Start feature-specific; promote to `shared/` only when ≥2 features genuinely need it.**
   Don't pre-emptively create `shared/services/xService.ts` for a one-feature concern — same
   "rule of three" reasoning as `architecture-best-practices` (principles.md §7, Hickey/Beck).
5. **Stores hold shared client state only** — not API calls, not business rules, not formatting.
   A store that starts accumulating those is a sign logic escaped its proper layer.
6. **Don't force every change through every layer.** A simple `GET /x/:id` can be
   Component → Hook → API directly; no service/domain needed. Services/domain earn their place
   when there's an actual multi-step workflow or a business rule to enforce (e.g. generation,
   delete-with-validation) — not for a single passthrough call. Five folders per feature is a
   menu, not a requirement.
7. **Frontend business validation is UX, not the source of truth.** The backend stays
   authoritative; `domain/` rules improve UX (fast feedback, disabled buttons) but never replace
   backend validation.

## Applying this in the web repo specifically

- When scaffolding the One Solution package, lay out `features/`, `shared/`, `api/`, `stores/`
  at the package's `src/` root per the structure above — not the flatter
  `components/pages/utils/helpers` layout `first-draft`/`qa` use today; that predates this doc
  and isn't the pattern to copy for this product.
- Keep all monorepo-wide conventions from `web/AGENTS.md` on top of this layering: import via
  `@web/<package>/src/...` (never relative imports across packages), CSS Modules per component,
  i18n `defaultValue` on every translation key, `@ets/design-system` components for new screens.

## Quick decision tree

UI → **Component** · React state/lifecycle → **Hook** · Application action/workflow →
**Service** · Business rule ("is this allowed?") → **Domain** · Talks to backend → **API** ·
Describes data shape → **Types** · Small generic helper → **Utils** · Shared state across
unrelated components → **Store**.
