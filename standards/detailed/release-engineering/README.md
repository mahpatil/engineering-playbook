# Release Engineering

Standards for getting a built artifact safely into production: how it is delivered and promoted, and how traffic is shifted to it.

## What is release engineering?

Release engineering covers everything between "the build passed" and "users are on the new version": delivery model, environment promotion, rollout strategy and rollback.

## Why it's required

Without shared defaults each team invents its own release path, and incidents show it: unreviewed production changes, all-at-once rollouts and slow manual rollbacks.

## Who it's for

Platform and SRE teams who set the defaults, and application teams who follow them.

---

## Documents

| Standard | What it covers |
|---|---|
| [Progressive Delivery](./progressive-delivery.md) | Canary and blue-green strategies, bake windows, metric gates, automated rollback |
| [Delivery Models and Environment Promotion](./gitops-promotions.md) | Pull, push and managed delivery; promotion between environments; drift; rollback |

## Where to Start

- Rolling out a service gradually? Start with [Progressive Delivery](./progressive-delivery.md).
- Deciding how code reaches a cluster? Start with [Delivery Models and Environment Promotion](./gitops-promotions.md).

## Guiding Principles

1. **Decouple deployment from release.** Running code and exposing it to users are separate steps.
2. **Metrics decide.** Promotion and rollback follow declared thresholds.
3. **Declare, don't hand-edit.** Desired state lives in version control.
4. **No long-lived deploy credentials.**
5. **Contain the blast radius.** Expose a small slice first.

Specific tools are examples, not requirements; each document says when an alternative fits.

## Related Standards

- [CI/CD Pipeline](../cicd-pipeline.md) builds the artifact these standards release.
- [Observability](../observability/README.md) supplies the signals behind rollout gates.
- [DevOps](../../overall/devops.md) covers the wider delivery practice.
- [Microservices](../microservices.md) defines the health-check and shutdown contracts rollouts rely on.
