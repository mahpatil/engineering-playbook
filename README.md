# Engineering Standards & Practices Playbook

> **Engineering North Star**: Production-grade patterns for modern cloud systems

A comprehensive collection of technical standards, best practices, architecture blueprints, and production-ready code samples for building scalable, resilient, and secure cloud-native applications.

## 📚 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Standards Catalog](#standards-catalog)
4. [For Technical Teams](#for-technical-teams)
5. [For Non-Technical Stakeholders](#for-non-technical-stakeholders)
6. [Contributing](#contributing)
7. [License](#license)


## 🎯 Overview

This repository contains battle-tested technical standards and practices developed over 20 years of building production systems at scale (American Express, Apple, and Fortune 500 enterprises). Each standard includes:

- **Architecture Blueprints**: Visual diagrams and system designs
- **Implementation Code**: Production-ready code samples
- **Non-Technical Guides**: Business-friendly explanations
- **Multi-Cloud Examples**: AWS, Azure, and GCP implementations

## 🚀 Quick Start
```bash
# Clone the repository
git clone https://github.com/mahpatil/engineering-playbook.git
cd engineering-playbook

# Explore standards
cd standards/overall
cat README.md
```

## 📖 Catalog


| Standard | Maturity | Cloud Support | README |
|----------|----------|---------------|--------|
| [Overall north star](./standards/overall/) | 🚧 Beta | Platform Agnostic Modern Architecture | [View](./standards/overall/README.md) |
| [Claude Templates](./templates/) | 🚧 Beta | Claude Code | [View](./templates/README.md) |
| [(dot)Claude Settings](./.claude) | 🚧 Beta | Claude Code | [View](./.claude/README.md) |
| Microservices | 📋 Planned | Platform Agnostic | [View](./standards/detailed/microservices.md)  |
| API Design | 📋 Planned | Platform Agnostic | [View](./standards/detailed/api-design.md)  |
| Data Architecture | 📋 Planned | AWS, Azure | Coming soon |
| Event-Driven Architecture - EDA | 📋 Planned | AWS, Azure, GCP | Coming soon |
| DevSecOps practices | 📋 Planned | Multi-cloud | Coming soon |
| CI/CD Pipeline | 📋 Planned | AWS, Azure, GCP | Coming soon |
| Observability standards | 📋 Planned | Multi-cloud | Coming soon |
| High Availability - HA | 📋 Planned | AWS, Azure | Coming soon |
| Scaling Patterns | 📋 Planned | AWS, Azure | Coming soon |
| Disaster Recovery - DR | 📋 Planned | AWS, Azure | Coming soon |


## 👨‍💻 For Technical Teams

### Engineers

Each standard includes production-ready code samples:
```python
# Example: Event-driven architecture
from events.producer import EventProducer

producer = EventProducer()
producer.publish_event(
    topic='orders',
    event_type='com.example.orders.created',
    data={'order_id': '12345', 'amount': 99.99}
)
```

### DevOps/SRE

Terraform modules, Kubernetes manifests, and CI/CD pipelines:
```terraform
# Example: Multi-AZ high availability setup
module "ha_infrastructure" {
  source = "./standards/high-availability/terraform/aws"
  
  region_primary   = "us-east-1"
  region_secondary = "us-west-2"
  rto_minutes      = 60
  rpo_seconds      = 5
}
```

### Architects

Architecture decision records (ADRs) and design patterns:

- When to use Event-Driven Architecture (coming soon)
- Multi-Cloud Strategy (coming soon)

## 💼 For Non-Technical Stakeholders

Each technical standard includes a **business-friendly explanation**:

- **What it is**: Plain English explanation
- **Why it matters**: Business impact (revenue, customer satisfaction, compliance)
- **Cost & ROI**: Investment requirements and returns
- **Risks**: What happens if we don't do this
- **Metrics**: How we measure success

Example: High Availability for Executives (coming soon)

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/new-standard`)
3. **Follow** the standard template (coming soon)
4. **Submit** a pull request


**Your input helps make these standards better for everyone.**

### Standard Quality Checklist

- [ ] Architecture blueprint included
- [ ] Production-ready code samples
- [ ] Multi-cloud examples (if applicable)
- [ ] Non-technical stakeholder guide
- [ ] Automated tests
- [ ] Documentation complete

## 📄 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

Built on lessons learned from:
- 20+ years of production systems in regulated industries such as finance services, healthcare, insurance, and enterprise environments
- Open source projects: Kubernetes, Kafka, Prometheus, OpenTelemetry
- Industry standards: OWASP, DORA, CNCF, CloudEvents
- Cloud platforms: AWS, Azure, GCP

## 📞 Contact

- **Maintainer**: Mahesh Patil
- **Email**: [mahesh@wonoments.com]
- **LinkedIn**: [linkedin.com/in/inspiredbytech](https://linkedin.com/in/inspiredbytech)

---

**Star ⭐ this repository if you find it helpful!**
