# React / Frontend Architecture

## Component design — apply the same coupling/cohesion lens as backend code
- **Container/presentational split (still useful as a mental model even without the old strict pattern)**: separate "what data does this need and where does it come from" from "how does this render." A component that both fetches data and has complex render logic has the same cohesion problem as a fat FastAPI router mixing HTTP and business logic.
- **Composition over configuration**: prefer composing smaller components (children/slots) over one large component with a growing list of boolean/enum props controlling its behavior. A component with 15 boolean props is usually several components wearing a trenchcoat.
- **Colocate state with where it's used**: lift state up only as far as actually needed for sharing, not reflexively to the top. Over-lifted state re-renders more of the tree than necessary and recreates prop-drilling problems the lifting was meant to avoid.

## State management — pick by scope, not by default library choice
| State type | Scope | Typical tool |
|---|---|---|
| Local UI state (form input, toggle, hover) | Single component | `useState`/`useReducer` |
| Shared UI state across a few components | Small subtree | Lifted state + context, or a small local store |
| Server/remote data (API responses) | App-wide, needs caching/invalidation | React Query / SWR / RTK Query — not plain global state |
| Global app state (auth, theme, feature flags) | App-wide, client-only | Context (low-frequency updates) or a dedicated store (Zustand/Redux) for high-frequency updates |

**The most common architectural mistake**: treating server data (API responses) as if it were client state — manually storing fetched data in `useState`/Redux and hand-rolling loading/error/cache/invalidation logic that a data-fetching library (React Query, SWR) already solves correctly, including request deduplication and background refetching. If the data comes from a server, prefer a server-state library over reinventing it in general-purpose client state.

## Data fetching patterns
- **Colocate fetching with the component that needs the data** (via hooks) rather than fetching everything at a top-level route and prop-drilling down — this mirrors the "bounded context" idea: each component owns its own data dependency, and it's easier to reason about what a component needs by reading its own hooks rather than tracing props through several layers.
- **Request waterfalls are the frontend version of the chatty-API antipattern** (see anti-patterns.md and api-design.md): if rendering one screen requires component A to fetch, then mount component B which fetches, then mount component C which fetches — sequentially — that's a waterfall. Prefer parallel fetching (fetch what you can up front, or use suspense-based patterns that parallelize) unless a genuine data dependency requires sequencing.

## Performance
- **Memoization (`useMemo`/`useCallback`/`React.memo`) is a targeted fix for a measured re-render problem, not a default habit.** Applying it everywhere adds cognitive overhead and can even hurt performance (memoization has its own cost) without a demonstrated win. Profile first (React DevTools Profiler), then memoize the specific expensive computation or the specific component re-rendering unnecessarily.
- **Code-splitting at route boundaries** (`React.lazy` + route-based chunks) is close to free performance — do this by default for any non-trivial app, rather than shipping one large bundle.
- **Virtualize long lists** (react-window or equivalent) rather than rendering hundreds/thousands of DOM nodes — this is the frontend equivalent of pagination (api-design.md): don't return/render more than the user can actually perceive at once.

## Backend-for-frontend / API shape alignment
When the same team owns both the FastAPI backend and the React frontend (as here), it's worth explicitly deciding: does the frontend consume the same general-purpose REST API a third party would, or does it get a tailored BFF layer shaped exactly for its screens? A tailored BFF reduces frontend-side data-wrangling and request waterfalls, at the cost of another layer to maintain — apply the same "is this split justified" reasoning from system-design-process.md rather than defaulting to either answer.
