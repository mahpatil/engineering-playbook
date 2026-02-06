# Contributing to Technical Standards Playbook

Thank you for your interest in contributing! This document provides guidelines for contributing to this repository.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Contribute](#how-to-contribute)
3. [Standard Template](#standard-template)
4. [Code Guidelines](#code-guidelines)
5. [Documentation Standards](#documentation-standards)
6. [Review Process](#review-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you agree to uphold:
- Respectful communication
- Constructive feedback
- Focus on technical merit
- Inclusive language

## How to Contribute

### Reporting Issues

We strive to continuously improve these standards based on your feedback.
Found a bug or have a suggestion?

1. Check [existing issues](https://github.com/mahpatil/technical-standards-playbook/issues)
2. Propose changes via RFC process
3. If new, create an issue with:
   - Clear title
   - Detailed description
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
4. Share success stories or challenges in #technical-standards-playbook

### Suggesting New Standards

Proposing a new standard?

1. Open an issue with `[New Standard]` prefix
2. Include:
   - Problem it solves
   - Proposed architecture
   - Similar existing solutions
   - Why this standard is needed

### Contributing Code

1. **Fork** the repository
2. **Create** a feature branch:
```bash
   git checkout -b feature/your-standard-name
```
3. **Make** your changes
4. **Test** thoroughly
5. **Commit** with clear messages:
```bash
   git commit -m "feat: Add Kubernetes autoscaling standard"
```
6. **Push** to your fork
7. **Create** a Pull Request

## Standard Template

Every new standard must follow this structure:
```
standards/your-standard-name/
├── README.md                    # Main documentation
├── architecture/
│   ├── blueprint.png            # Architecture diagram
│   └── decision-tree.md         # When to use
├── examples/
│   ├── aws/                     # AWS implementation
│   ├── azure/                   # Azure implementation
│   └── gcp/                     # GCP implementation (optional)
├── docs/
│   ├── for-executives.md        # Non-technical guide
│   ├── troubleshooting.md       # Common issues
│   └── metrics.md               # Success metrics
└── tests/
    └── validation-tests.sh      # Automated tests
```

### README.md Template
```markdown
# [Standard Name]

> **North Star**: "[One-sentence goal]"

## Overview
[2-3 paragraph overview]

## 📁 Directory Structure
[Show directory tree]

## 🎯 Key Principles
[3-5 core principles]

## 🏗️ Why these Standards Matter
[Architecture diagram and explanation]

## 🏗️ When to Use These Standards
[Architecture diagram and explanation]

## 🏗️ Architecture
[Architecture diagram and explanation]

## 🚀 Quick Start
[Copy-paste commands to get started]

## 📊 Metrics
[How to measure success]

## 💼 For Executives
[Business-friendly summary]

## 🐛 Troubleshooting
[Common issues table]

## 📚 Additional Resources
[External links]
```

## Code Guidelines

### Python
```python
# Use type hints
def process_event(event: Dict[str, Any]) -> bool:
    """
    Process incoming event.
    
    Args:
        event: Event dictionary containing data
        
    Returns:
        True if successful, False otherwise
    """
    pass

# Follow PEP 8
# Use meaningful variable names
# Add docstrings to all functions
# Include error handling
```

### Terraform
```terraform
# Use consistent naming
resource "aws_instance" "web_server" {
  ami           = var.ami_id
  instance_type = var.instance_type
  
  tags = {
    Name        = "web-server"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Add comments for complex logic
# Use variables for configurable values
# Include outputs
```

### YAML
```yaml
# Use 2-space indentation
# Include comments for clarity
name: CI/CD Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
```

## Documentation Standards

### Architecture Diagrams

- Use mermaid (preferred) or draw.io or Lucidchart
- Export as PNG (1920x1080 recommended)
- Include legend
- Use consistent colors/shapes
- Save source file (`.drawio` or `.lucidchart`)

### Executive Guides

Format:
```markdown
# [Standard Name] for Executives

## What It Is
[Plain English explanation]

## Why It Matters
[Business impact]

## Cost & ROI
[Investment and returns]

## Risks
[What happens without this]

## Success Metrics
[How we measure]
```

### Code Comments

- Explain **why**, not **what**
- Add context for complex logic
- Reference tickets/issues where relevant
- Keep comments up-to-date with code

## Review Process

### Pull Request Checklist

Before submitting:

- [ ] Follows standard template
- [ ] Includes architecture diagram
- [ ] Has production-ready code examples
- [ ] Multi-cloud examples (if applicable)
- [ ] Executive guide included
- [ ] Tests pass locally
- [ ] Documentation complete
- [ ] No secrets in code
- [ ] CHANGELOG.md updated

### Review Criteria

Pull requests are reviewed for:

1. **Technical Accuracy**: Does it work as described?
2. **Completeness**: Are all sections filled?
3. **Code Quality**: Follows best practices?
4. **Documentation**: Clear and comprehensive?
5. **Business Value**: Explains "why" for non-technical audiences?

### Review Timeline

- Initial review: Within 3 business days
- Follow-up: Within 2 business days of changes
- Merge: After 2 approving reviews

## Questions?

- **General questions**: Open a [discussion](https://github.com/your-org/technical-standards-playbook/discussions)
- **Bug reports**: Open an [issue](https://github.com/your-org/technical-standards-playbook/issues)
- **Security issues**: Email security@your-org.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🙏