Title: Engineering Principles

1. Core tenets
- Clarity over cleverness: Optimize for readability and explicitness.
- Small, safe changes: Incremental delivery with tests and feature flags.
- Separation of concerns: Isolate domains, interfaces, and implementations.
- Defensive boundaries: Validate inputs at edges; trust internal invariants.
- Observability-first: Logs, metrics, traces are first-class.

2. Tradeoffs
- Performance vs maintainability: Prefer maintainable solutions; optimize hotspots proven by profiling.
- Consistency vs local optimization: Favor repo-wide conventions; exceptions must be justified and documented.
- Abstraction vs simplicity: Abstract only repeated patterns; avoid premature indirection.

3. Security & privacy
- Least privilege: Minimize permissions and accessible data.
- Input validation: Sanitize at boundaries; reject malformed or unexpected inputs.
- Secrets management: Never hardcode; use vaults/env; rotate keys.
- PII handling: Mask at rest and in logs; adhere to data minimization.

4. Reliability
- Idempotence: Make external effects safe to retry.
- Timeouts & retries: Bounded retries with backoff; circuit breakers for unstable dependencies.
- Fail fast: Detect and surface errors early; avoid silent failures.

5. Performance targets
- Latency budgets: Define per endpoint/service SLOs; e.g., p95 ≤ 250ms for critical APIs.
- Resource usage: Bound memory/CPU; monitor and alert on regressions.
- Start-up time: Services start within defined thresholds; lazy-init non-critical components.

6. Java-specific
- Immutability: Use records and immutable collections where possible.
- Interfaces-first: Define clear interfaces; inject implementations; avoid static singletons.
- Concurrency: Prefer `CompletableFuture`/structured concurrency; avoid unbounded thread pools.

7. Python-specific
- Functional core / imperative shell: Keep business logic pure; isolate IO.
- Type-safe boundaries: Strict mypy at interfaces; treat `Any` as smell.
- Concurrency: Use `asyncio` or `concurrent.futures` appropriately; no shared mutable state across threads.

8. Cloud-Native Microservices
- Statelessness: Services must be stateless; externalize all state to persistent stores for horizontal scaling.
- Resilience Patterns: Implement circuit breakers, retries with backoff, timeouts, and bulkheads for fault isolation.
- Infrastructure as Code: All infrastructure, configuration, and deployments are version-controlled, auditable code.
- Immutability: Use immutable containers and deployments; avoid in-place updates to ensure consistency and simplify rollbacks.
- Backwards Compatibility: Maintain API stability; support multiple versions during transitions for independent service evolution.
- Cost Optimization: Right-size resources, monitor cloud spending, use auto-scaling and spot instances to minimize waste.
- Team Autonomy: Organize teams around business domains; enable independent service ownership and deployment (Conway's Law).
- Graceful Degradation: Services fail safely with reduced functionality; prioritize critical paths to prevent cascade failures.
