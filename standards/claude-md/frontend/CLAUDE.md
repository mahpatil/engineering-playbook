# Frontend Standards

Extends ../CLAUDE.md.

React + TypeScript web apps. HTTP status semantics: see `../api/CLAUDE.md`.

## Approved stack
Versions are minimums; follow current stable within the major.

| Concern | Choice |
|---|---|
| UI | React >= 19, function components only |
| Language | TypeScript >= 5.5, `strict` |
| Build | Vite (no new Webpack projects) |
| Server state | TanStack Query v5 |
| Global UI state | Zustand (modals, theme); never for server data |
| Local state | `useState` / `useReducer` |
| URL state | Router search params (filters, tabs) |
| Routing | React Router v7 or TanStack Router; one per project |
| Forms | React Hook Form + Zod (>= 4) |
| Styling | CSS Modules or Tailwind (>= 4); no runtime CSS-in-JS |
| API client | `openapi-typescript` + `openapi-fetch`, generated from the API spec |
| i18n | `react-i18next`; strings in `public/locales/{lang}/{ns}.json`, `Intl` for formats, logical CSS properties |
| Tests | Vitest + React Testing Library + `userEvent`; Playwright for E2E |

## TypeScript
```json
{ "compilerOptions": { "strict": true, "noUncheckedIndexedAccess": true,
  "exactOptionalPropertyTypes": true, "noImplicitReturns": true,
  "noFallthroughCasesInSwitch": true, "verbatimModuleSyntax": true } }
```
- No `any` and no `as` to silence errors (enforced by lint); use `unknown` and narrow; use `satisfies` to check literals.

## Components
- Files: `PascalCase.tsx` per component; hooks `useX.ts`; co-locate test and styles in the component folder.
- Split a component when it mixes data fetching with rendering, exceeds ~150 lines of JSX, or has more than two unrelated render states.
- Use a `variant` prop instead of boolean flags (`isPrimary`, `isDanger`). Callback props are `onEvent`.
- Every route and independent page section has an Error Boundary.
- Every data-driven view handles loading (skeleton), error (message plus retry) and empty (guidance) states.
- Do not hand-write `memo`/`useMemo`/`useCallback` where React Compiler is enabled; otherwise only after profiling.

## Data fetching
- Remote data lives in TanStack Query only; never mirror it into `useState` or Zustand.
- Query keys are arrays from a per-feature key factory: `['orders', 'detail', id]`.
- Set `staleTime` explicitly (default 30 s); mutations invalidate or update the affected keys.
- Map API problem+json errors to UI messages in one shared error handler; show `errors[]` field messages inline on forms.
- Send `Idempotency-Key` on retried POSTs.

## Auth and browser security
- Tokens in memory or `HttpOnly` cookies; never `localStorage`.
- No `dangerouslySetInnerHTML` without DOMPurify. CSP set at the CDN or server, no inline scripts. SRI on third-party scripts. Validate redirect targets.

## Accessibility
Target: WCAG 2.2 AA.
- Semantic elements first (`<button>`, not `<div onClick>`); visible focus; keyboard-operable; contrast 4.5:1 (3:1 large text and UI components); targets at least 24x24 CSS px.
- Dynamic updates (toasts, async status) use `aria-live`; on route change, move focus to the page heading.
- Enforced by `eslint-plugin-jsx-a11y` (strict), `vitest-axe` in unit tests and `@axe-core/playwright` in E2E, failing on any violation. Keyboard-only pass before each major UI release; screen-reader pass quarterly.

## Performance budgets
| Metric | Budget |
|---|---|
| LCP | < 2.5 s (p75) |
| INP | < 200 ms (p75) |
| CLS | < 0.1 |
| Initial JS per route | <= 250 KB gzipped |

- Lighthouse CI asserts these on every PR (lab INP is unavailable; assert TBT < 200 ms and track INP via RUM). Bundle size is enforced by `size-limit` or `vite-bundle-visualizer` in CI.
- Lazy-load routes by default; lazy-load heavy widgets (editors, charts, date pickers).

## Testing
- Query priority: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`. Use `userEvent`, not `fireEvent`. Do not mock child components.
- Mock the network with MSW.
- Playwright covers critical journeys only: auth, each core happy path, key error paths.

## Lint and CI enforcement
```ts
// eslint.config.ts (typescript-eslint flat config)
export default tseslint.config(
  tseslint.configs.strictTypeChecked,
  reactHooks.configs['recommended-latest'],
  jsxA11y.flatConfigs.strict,
  { rules: { 'react-hooks/exhaustive-deps': 'error',
             'no-console': ['error', { allow: ['warn', 'error'] }],
             '@typescript-eslint/no-explicit-any': 'error' } },
);
```
- CI: `tsc --noEmit`, `eslint --max-warnings 0`, `prettier --check`, Vitest, build, Lighthouse CI, Playwright.
