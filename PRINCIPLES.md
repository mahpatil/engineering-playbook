# Engineering Principles

Quick reference for core engineering principles. For detailed standards, see [standards/](./standards/).

---

## Core Tenets

- **Clarity over cleverness**: Optimize for readability and explicitness
- **Small, safe changes**: Incremental delivery with tests and feature flags
- **Separation of concerns**: Isolate domains, interfaces, and implementations
- **Defensive boundaries**: Validate inputs at edges; trust internal invariants
- **Observability-first**: Logs, metrics, traces are first-class citizens
- **Consistency across teams**: Shared practices, vocabulary, and decision-making
- **Data-driven decisions**: Objective criteria, ADRs, and metrics over opinions
- **Quality & security are everyone's responsibility**: Shift-left; built in, not bolted on
- **Living documentation**: Auto-generated from code; manually document only ADRs and context
- **Continuous learning**: Retrospectives, post-mortems, evolving standards

---

## Cloud-Native Principles

1. **Composable Architecture & DDD** - Bounded contexts, ubiquitous language
2. **API-First & Contract-Driven** - Independent services with clear contracts
3. **Cloud Portability** - Avoid vendor lock-in, use open standards
4. **Observability** - Tracing, logging, metrics, alerting
5. **Zero Trust Security** - Authenticate, authorize, encrypt all flows
6. **Performance Optimization** - Caching, compression, efficient algorithms
7. **High Availability** - Redundancy, failover, graceful degradation
8. **Reliability & Resilience** - Fault tolerance, chaos engineering
9. **Cost Optimization** - Right-sizing, auto-scaling, FinOps
10. **Automation First** - CI/CD, automated testing, security scanning
11. **Infrastructure as Code** - Version-controlled, repeatable deployments
12. **AI-First Design** - Inference endpoints, feature stores, feedback loops from inception
13. **Open Source & Open Standards** - Prefer OAUTH, OpenTelemetry, Kubernetes over proprietary

---

## Tradeoffs

| Decision | Guidance |
|----------|----------|
| Performance vs Maintainability | Prefer maintainable; optimize proven hotspots |
| Consistency vs Local Optimization | Favor org-wide conventions |
| Abstraction vs Simplicity | Abstract only repeated patterns (Rule of Three) |

---

## Technology Selection

- Open standards preferred
- Libraries with zero critical/high vulnerabilities
- Active maintenance and community support
- Clear licensing compatible with commercial use
- Performance characteristics matching requirements
- AI/ML frameworks with production-ready serving capabilities

---

## Detailed Standards

| Document | Content |
|----------|---------|
| [principles.md](./standards/overall/principles.md) | Full principles with rationale |
| [patterns.md](./standards/overall/patterns.md) | Architecture patterns |
| [tech-stack.md](./standards/overall/tech-stack.md) | Technology stack standards |
| [devops.md](./standards/overall/devops.md) | CI/CD and DevOps |
| [metrics.md](./standards/overall/metrics.md) | Observability and metrics |
| [checklists.md](./standards/overall/checklists.md) | Implementation checklists |
| [decision-framework.md](./standards/overall/decision-framework.md) | Decision framework |
| [glossary.md](./standards/overall/glossary.md) | Glossary of terms |
