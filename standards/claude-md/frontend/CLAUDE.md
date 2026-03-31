# Frontend Standards

Read `../CLAUDE.md` first. This file extends those principles for frontend applications built with React and TypeScript.

---

## Technology Stack

| Concern | Choice | Notes |
|---|---|---|
| Framework | React 19+ | Functional components only — no class components |
| Language | TypeScript 5.x strict | `"strict": true` in `tsconfig.json` — no exceptions |
| Build | Vite | No Webpack for new projects |
| State (local) | `useState`, `useReducer` | Prefer local; lift only when necessary |
| State (server) | TanStack Query (React Query) | Canonical choice for remote data; replaces Redux for most cases |
| State (global UI) | Zustand | For lightweight global UI state (modals, themes) |
| Styling | CSS Modules or Tailwind CSS | No CSS-in-JS (runtime performance cost) |
| Testing | Vitest + React Testing Library | Unit and integration tests |
| E2E | Playwright | Critical user journeys |
| Forms | React Hook Form + Zod | Validation co-located with schema |
| Routing | React Router v7 / TanStack Router | Project-consistent — don't mix |
| API client | Generated from OpenAPI spec | Use `openapi-typescript` + `openapi-fetch` |

---

## TypeScript Standards

**`strict: true` is mandatory and non-negotiable.** This enables:
- `noImplicitAny`
- `strictNullChecks`
- `strictFunctionTypes`
- `strictPropertyInitialization`

Additional required compiler options:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

### Type Usage

```typescript
// GOOD — explicit, narrow types
interface Order {
  id: string;
  status: 'PENDING' | 'CONFIRMED' | 'CANCELLED';
  total: Money;
  createdAt: Date;
}

// BAD — structural type lost, defeats TypeScript
const processOrder = (order: any) => { ... }

// BAD — overly broad
const processOrder = (order: object) => { ... }
```

- Use `type` for unions and intersections. Use `interface` for object shapes (they can be extended).
- Never use `as` to cast away type errors. Fix the underlying type.
- `unknown` over `any` when the type is genuinely unknown — it forces handling before use.
- Use `satisfies` to validate objects against a type while preserving inference.

---

## Component Design

### Single Responsibility

Each component does one thing. Signs a component is doing too much:
- More than ~150 lines of JSX
- More than 3-4 props that are logically unrelated
- Contains both data fetching and UI rendering
- Has conditional rendering for more than 2 significantly different states

Split into smaller components. A component that just renders data is easier to test and reuse.

### Component Patterns

```typescript
// GOOD — clear prop interface, single responsibility
interface OrderSummaryCardProps {
  order: Order;
  onConfirm: (orderId: string) => void;
  isLoading?: boolean;
}

export function OrderSummaryCard({ order, onConfirm, isLoading = false }: OrderSummaryCardProps) {
  return (
    <article aria-labelledby={`order-${order.id}-title`}>
      <h2 id={`order-${order.id}-title`}>Order {order.id}</h2>
      <OrderStatusBadge status={order.status} />
      <OrderTotalDisplay total={order.total} />
      <ConfirmButton
        orderId={order.id}
        onConfirm={onConfirm}
        disabled={order.status !== 'PENDING'}
        isLoading={isLoading}
      />
    </article>
  );
}
```

### Naming

- Components: `PascalCase`.
- Files: `PascalCase.tsx` matching the component name.
- Hooks: `useCamelCase.ts`.
- Utilities: `camelCase.ts`.
- Constants: `SCREAMING_SNAKE_CASE` in a dedicated `constants.ts`.
- Co-locate component, styles, and tests: `OrderSummaryCard/index.tsx`, `OrderSummaryCard/OrderSummaryCard.test.tsx`.

### Props

- Avoid boolean prop flags that encode a type variant (`isAdmin`, `isPrimary`, `isDanger`). Use a `variant` prop instead: `variant="primary" | "danger"`.
- Avoid passing large objects as props to pure display components — pass only what is rendered. This makes the component's interface explicit and prevents unnecessary re-renders.
- Callback props are named `onEvent` (e.g. `onClick`, `onSubmit`, `onOrderConfirmed`).

---

## State Management

### Decision Rule

| State Type | Where it Lives |
|---|---|
| Local UI (open/closed, form field) | `useState` in the component |
| Derived from other state | `useMemo` / derived inside component |
| Shared between sibling components | Lift to common parent |
| Server data (fetched from API) | TanStack Query |
| Global UI (modal state, theme, auth) | Zustand |
| URL-driven (filters, selected tab) | URL search params via React Router |

**Do not reach for global state first.** Most state is local. Start local, lift only when necessary.

### TanStack Query

```typescript
// GOOD — query with typed data, error, and loading states
function useOrder(orderId: string) {
  return useQuery({
    queryKey: ['orders', orderId],
    queryFn: () => ordersApi.getOrder(orderId),
    staleTime: 30_000,  // 30s — don't refetch on focus if data is fresh
  });
}

// GOOD — mutation with optimistic update
function useConfirmOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) => ordersApi.confirmOrder(orderId),
    onSuccess: (data, orderId) => {
      queryClient.setQueryData(['orders', orderId], data);
    },
    onError: (error) => {
      toast.error(`Failed to confirm order: ${error.message}`);
    },
  });
}
```

Do not use TanStack Query for local-only state. Do not use `useState` for remote data.

---

## Accessibility (WCAG 2.1 AA)

Accessibility is not optional. Every component meets WCAG 2.1 AA compliance at minimum.

### Non-Negotiables

- **Semantic HTML first.** Use `<button>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<header>`, `<footer>` correctly. Do not use `<div onClick>` where a `<button>` is appropriate.
- **Keyboard navigation.** Every interactive element is reachable and operable by keyboard alone. Focus order matches visual order.
- **Focus visible.** Never use `outline: none` without providing a replacement focus indicator.
- **Color contrast.** Text must meet 4.5:1 contrast ratio (3:1 for large text). Do not rely on colour alone to convey meaning.
- **ARIA labels.** All interactive elements have accessible names. Icon buttons require `aria-label`. Form inputs have associated `<label>`.
- **Live regions.** Dynamic content updates (toast notifications, async status changes) use `aria-live` to announce to screen readers.

```tsx
// GOOD — button with accessible name, loading state communicated
<button
  type="button"
  onClick={() => onConfirm(orderId)}
  disabled={isLoading}
  aria-busy={isLoading}
  aria-label={isLoading ? 'Confirming order, please wait' : 'Confirm order'}
>
  {isLoading ? <Spinner aria-hidden="true" /> : 'Confirm Order'}
</button>

// BAD — clickable div, no keyboard access, no accessible name
<div onClick={() => onConfirm(orderId)} className="btn">Confirm</div>
```

### Testing Accessibility

- Use `jest-axe` in unit tests to catch common violations automatically.
- Use Playwright with `axe-playwright` in E2E tests.
- Manual test with keyboard-only navigation before every significant UI release.
- Manual test with a screen reader (VoiceOver on macOS, NVDA on Windows) quarterly.

---

## Performance

### Core Web Vitals Targets

| Metric | Target |
|---|---|
| LCP (Largest Contentful Paint) | < 2.5s |
| CLS (Cumulative Layout Shift) | < 0.1 |
| INP (Interaction to Next Paint) | < 200ms |
| FCP (First Contentful Paint) | < 1.8s |
| TTFB (Time to First Byte) | < 800ms |

Measure with Lighthouse in CI on every build. Block on regression below these targets.

### Code Splitting

```typescript
// GOOD — lazy load heavy routes
const OrderDashboard = lazy(() => import('./pages/OrderDashboard'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));

// Wrap in Suspense at the route level
<Suspense fallback={<PageSkeleton />}>
  <Routes>
    <Route path="/orders" element={<OrderDashboard />} />
    <Route path="/reports" element={<ReportsPage />} />
  </Routes>
</Suspense>
```

- Split at route level by default.
- Split heavy components (rich text editors, chart libraries, date pickers) with `lazy()`.
- Avoid splitting small components — the network round-trip overhead is not worth it.

### Render Performance

- Use `React.memo` only when profiling proves a component re-renders unnecessarily due to parent re-renders.
- Use `useMemo` and `useCallback` only for expensive computations and stable callback references (e.g. passed to memoized children). Do not premature-optimise every function.
- Avoid object and array literals in JSX props — they create new references on every render.

```tsx
// BAD — new object on every render
<Component style={{ color: 'red' }} options={['a', 'b']} />

// GOOD — stable references
const STYLE = { color: 'red' } as const;
const OPTIONS = ['a', 'b'] as const;
<Component style={STYLE} options={OPTIONS} />
```

### Asset Optimisation

- Images: use `<img loading="lazy" decoding="async">` for below-fold images. Use `width` and `height` attributes to prevent CLS.
- Use modern image formats (WebP/AVIF) with PNG/JPEG fallbacks.
- Fonts: `font-display: swap`. Preload critical fonts.
- Bundle analysis: run `vite-bundle-visualizer` on every release. Investigate bundles > 250KB (gzipped).

---

## Testing

### Unit and Integration Tests (Vitest + React Testing Library)

Test **behaviour**, not implementation. Query by accessible role and label — not by CSS selector or test ID.

```typescript
// GOOD — tests what the user sees and does
it('should disable the confirm button while the request is in flight', async () => {
  const user = userEvent.setup();
  render(<OrderSummaryCard order={pendingOrder} onConfirm={vi.fn()} isLoading={true} />);

  const button = screen.getByRole('button', { name: /confirm order/i });
  expect(button).toBeDisabled();
  expect(button).toHaveAttribute('aria-busy', 'true');
});

// BAD — tests implementation detail, brittle
it('renders correctly', () => {
  const { container } = render(<OrderSummaryCard order={pendingOrder} onConfirm={vi.fn()} />);
  expect(container.querySelector('.confirm-btn')).toBeInTheDocument();
});
```

Rules:
- Query priority: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- Use `getByTestId` only as a last resort, and only with a `data-testid` attribute, never a CSS class.
- `userEvent` over `fireEvent` — it simulates real user interactions including pointer and keyboard events.
- Wrap async assertions in `waitFor` or use async `userEvent`.
- Avoid mocking child components — test the composed tree for integration tests.

### E2E Tests (Playwright)

Cover the top 5-10 critical user journeys:
1. User login and authentication
2. Primary "happy path" for each core feature
3. Key error paths (validation, network failure)
4. Payment / checkout (if applicable)

```typescript
test('user can create and confirm an order', async ({ page }) => {
  await page.goto('/orders/new');
  await page.getByLabel('Customer ID').fill('cust-123');
  await page.getByRole('button', { name: 'Add Item' }).click();
  await page.getByLabel('Product').selectOption('prod-456');
  await page.getByRole('button', { name: 'Create Order' }).click();

  await expect(page.getByRole('heading', { name: /order created/i })).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('PENDING');
});
```

---

## Error Handling

### Error Boundaries

Every route and every "independent section" of the UI has an Error Boundary. A crash in the order list must not crash the navigation or the rest of the page.

```tsx
function OrdersDashboard() {
  return (
    <DashboardLayout>
      <ErrorBoundary fallback={<SectionError section="Order List" />}>
        <OrderList />
      </ErrorBoundary>
      <ErrorBoundary fallback={<SectionError section="Order Summary" />}>
        <OrderSummaryPanel />
      </ErrorBoundary>
    </DashboardLayout>
  );
}
```

### Network Error States

Every data-fetching component handles three states explicitly:
1. **Loading** — skeleton or spinner (never a blank space)
2. **Error** — meaningful error message with a retry option
3. **Empty** — an empty state with guidance (not a blank list)

```tsx
function OrderList() {
  const { data, isLoading, error, refetch } = useOrders();

  if (isLoading) return <OrderListSkeleton />;
  if (error) return <ErrorMessage message="Could not load orders" onRetry={refetch} />;
  if (!data?.length) return <EmptyState message="No orders yet" />;

  return <ul>{data.map(order => <OrderListItem key={order.id} order={order} />)}</ul>;
}
```

---

## Security

- **XSS**: Never use `dangerouslySetInnerHTML`. If it is truly necessary (e.g. rendering CMS content), sanitize with DOMPurify before rendering.
- **Content Security Policy**: Configure CSP headers at the server/CDN level. Do not inline scripts.
- **Sensitive data**: Do not store JWTs, API keys, or PII in `localStorage`. Use in-memory storage for tokens; use `HttpOnly` cookies when possible.
- **Third-party scripts**: Every third-party script is evaluated for necessity and privacy implications. Use `integrity` (SRI) for scripts loaded from external CDNs.
- **Open redirects**: Validate redirect URLs. Never redirect to a caller-supplied URL without validation.

---

## Internationalisation (i18n)

For applications serving multiple locales:
- Use `react-i18next`. Externalise all user-visible strings from day one.
- Store translations in `public/locales/{lang}/{namespace}.json`.
- Use `t('key')` consistently — no hardcoded English strings in JSX.
- Format dates, numbers, and currencies via `Intl` APIs, not manual formatting.
- Support RTL layouts using logical CSS properties (`margin-inline-start` not `margin-left`).

Even for initially single-locale apps, write code as if i18n will be added. It almost always is.

---

## Code Standards

### ESLint

Required rules (configured in `eslint.config.ts`):

```typescript
export default [
  ...reactPlugin.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'no-console': ['error', { allow: ['warn', 'error'] }],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': 'error',
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/aria-proptypes': 'error',
    }
  }
];
```

### Formatting

- Prettier for all formatting. No manual formatting debates.
- `prettier --check` fails CI if files are not formatted.
- 2-space indentation. Single quotes. No semicolons (or all semicolons — be consistent per project).

---

## Related Standards

- `../CLAUDE.md` — Root engineering principles
- `../api/CLAUDE.md` — API contracts and response shapes (consumed by the frontend)
- `standards/overall/tech-stack.md` — Approved frontend libraries and tooling
