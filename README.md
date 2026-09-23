# Engineering Standards & Practices Playbook

> **Production-grade thinking for modern cloud systems.**
>
> Architecture patterns, engineering standards, and practical tools for teams building systems that need to scale, recover, and earn trust.

<p align="left">
  <img src="https://img.shields.io/github/stars/mahpatil/engineering-playbook?style=for-the-badge&logo=github&label=STARS&color=F4B400" alt="GitHub stars">
  <a href="https://github.com/mahpatil/engineering-playbook/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/mahpatil/engineering-playbook/validate.yml?style=for-the-badge&label=QUALITY%20GATE&color=2E7D32" alt="Quality gate status"></a>
  <a href="https://github.com/mahpatil/engineering-playbook/releases"><img src="https://img.shields.io/github/v/release/mahpatil/engineering-playbook?style=for-the-badge&label=LATEST%20RELEASE&color=1565C0" alt="Latest release"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/mahpatil/engineering-playbook?style=for-the-badge&label=LICENSE&color=6A1B9A" alt="MIT license"></a>
</p>

<p align="left">
  <a href="#start-here">Start here</a> ·
  <a href="#the-catalog">Browse the catalog</a> ·
  <a href="#quality-gates">Quality gates</a> ·
  <a href="#versioning-and-releases">Releases</a> ·
  <a href="./CONTRIBUTING.md">Contribute</a>
</p>

<a id="start-here"></a>

## 🧭 Start Here

This is a living engineering reference for architects, engineers, platform teams, and technical leaders. It brings together the decisions and habits that make cloud-native systems resilient, observable, secure, and easier to evolve.

| You need to... | Go to... |
|---|---|
| Understand the principles behind the playbook | [Engineering principles](./PRINCIPLES.md) |
| Choose an architecture approach | [Overall standards](./standards/overall/README.md) |
| Design APIs, data, integrations, or networks | [Detailed standards](./standards/detailed/) |
| Set up an AI-assisted workstation | [Developer tools](./tools/tools.md) |
| Build reusable agent workflows | [Agent catalog](./agents/README.md) |
| Learn the concepts step by step | [Training path](./training/README.md) |

## ✨ What You’ll Find

- **Architecture blueprints** for scalable, resilient, and secure systems
- **Implementation guidance** with practical patterns and examples
- **Multi-cloud perspectives** across AWS, Azure, and GCP
- **Executive-friendly context** covering cost, risk, outcomes, and metrics
- **AI-native practices** for tools, hooks, agents, and human-in-the-loop delivery

## 🚀 Quick Start

```bash
git clone https://github.com/mahpatil/engineering-playbook.git
cd engineering-playbook

# Start with the principles and the overall standards index
open PRINCIPLES.md
open standards/overall/README.md
```

Prefer the command line? Replace `open` with `less`, `bat`, or your editor of choice.

<a id="the-catalog"></a>

## 📚 The Catalog

| Standard | Maturity | Focus | Explore |
|---|---|---|---|
| [Overall north star](./standards/overall/) | ✅ Stable | Platform-agnostic architecture | [View](./standards/overall/README.md) |
| [Microservices](./standards/detailed/microservices.md) | ✅ Stable | Service boundaries and operations | [View](./standards/detailed/microservices.md) |
| [API design](./standards/detailed/api-design.md) | 📋 Beta | Contracts and interfaces | [View](./standards/detailed/api-design.md) |
| [Data architecture](./standards/detailed/data/README.md) | 📋 Beta | AWS, Azure, and GCP | [View](./standards/detailed/data/README.md) |
| [Cloud network topology](./standards/detailed/networking/cloud-network-topology.md) | ✅ Stable | Hub-and-spoke, PCI, gateways | [View](./standards/detailed/networking/cloud-network-topology.md) |
| [Integration patterns](./standards/detailed/integration/data-integration-patterns.md) | 📋 Beta | Events and data movement | [View](./standards/detailed/integration/data-integration-patterns.md) |
| [CI/CD and DevSecOps](./standards/detailed/cicd-pipeline.md) | 📋 Planned | Delivery and quality gates | [View](./standards/detailed/cicd-pipeline.md) |
| [Observability](./standards/detailed/observability/README.md) | 📋 Beta | Logs, metrics, traces, SLOs | [View](./standards/detailed/observability/README.md) |
| [Developer tools](./tools/tools.md) | 📋 Beta | Workstation setup and hooks | [View](./tools/tools.md) |
| [Agent catalog](./agents/README.md) | 🚧 Beta | Reusable engineering agents | [View](./agents/README.md) |
| [Claude templates](./templates/) | 🚧 Beta | AI-assisted delivery | [View](./templates/README.md) |

<a id="quality-gates"></a>

## 🛡️ Quality Gates

Every pull request should leave the playbook more trustworthy than it found it. The repository quality gate checks:

1. **Markdown style** with `markdownlint-cli2`
2. **Internal and external links** with `lychee`
3. **Whitespace and patch hygiene** with `git diff --check`
4. **Review completeness** against the [contribution checklist](./CONTRIBUTING.md)

Run the same checks locally before opening a pull request:

```bash
npx --yes markdownlint-cli2 "**/*.md" "#node_modules"
npx --yes markdown-link-check README.md
git diff --check
```

The GitHub Actions quality gate runs on pushes and pull requests. A change is ready to merge when the checks pass and the relevant standard has been reviewed for technical accuracy, examples, and links.

<a id="versioning-and-releases"></a>

## 🏷️ Versioning and Releases

The first published snapshot is [`v0.1.0`](https://github.com/mahpatil/engineering-playbook/releases/tag/v0.1.0). Future snapshots use **Semantic Versioning**:

- `MAJOR`: a reorganized or incompatible documentation structure
- `MINOR`: a new standard, training module, or significant guidance area
- `PATCH`: corrections, clarifications, examples, and link fixes

Release flow:

```text
change -> pull request -> quality gate -> merge to main
              |
              v
          tag vMAJOR.MINOR.PATCH
              |
              v
            GitHub release notes
```

To publish a release after changes land on `main`, create and push a SemVer tag:

```bash
git checkout main
git pull --ff-only
git tag v0.2.0
git push origin v0.2.0
```

Pushing a `v*` tag starts the **Release** workflow. The workflow accepts only `vMAJOR.MINOR.PATCH` tags, creates the GitHub release, and generates release notes from merged pull requests. There is no manual release step in GitHub Actions. Keep notable changes grouped in the release description and ensure the quality gate passes before tagging.

## 👥 For Technical Teams

### Engineers

Use the standards as a design review companion: start with the relevant principle, compare the available patterns, then adapt the examples to your runtime and cloud boundary.

### Platform and SRE teams

Use the networking, DevSecOps, CI/CD, high-availability, scaling, disaster-recovery, and observability material to turn operational expectations into repeatable controls.

### Architects and technical leaders

Use the decision frameworks, metrics, ADR guidance, and executive summaries to make tradeoffs explicit and durable.

## 💼 For Non-Technical Stakeholders

The playbook connects technical choices to business outcomes: customer experience, resilience, compliance, cost, delivery speed, and measurable risk reduction.

## 🤝 Contributing

1. Fork the repository and create a focused feature branch.
2. Add or update the relevant standard, example, or training material.
3. Run the [quality checks](#quality-gates) locally.
4. Update links, maturity status, and release notes when appropriate.
5. Open a pull request using a clear, outcome-oriented description.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution and review guidelines.

## 📄 License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

## 🙏 Acknowledgments

Built from lessons learned in regulated finance, healthcare, insurance, and enterprise environments, and informed by Kubernetes, Kafka, Prometheus, OpenTelemetry, OWASP, DORA, CNCF, CloudEvents, AWS, Azure, and GCP.

## 📞 Contact

- **Maintainer:** Mahesh Patil
- **Email:** [mahesh@wonoments.com](mailto:mahesh@wonoments.com)
- **LinkedIn:** [linkedin.com/in/inspiredbytech](https://linkedin.com/in/inspiredbytech)

---
⭐ If this playbook helps your team make a better engineering decision, star the repository and share the standard that helped.
<!-- End of README -->
