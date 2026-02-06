# Core guiding princiles
## The 3 Ps framework

PRODUCT: Build what creates value
PLATFORM: Enable teams to move fast
PEOPLE: Invest in capabilities, not just capacity

## Core engineering Values

### 1. **Consistency Across Teams**

All teams follow the same foundational principles, creating predictability and enabling collaboration across the organization.

**What this means:**
- Shared engineering values and practices
- Common technical vocabulary and terminology
- Standardized decision-making processes
- Unified quality and reliability expectations

**Example:** When an engineer moves from one team to another, they encounter familiar practices, tools, and approaches rather than starting from scratch.

### 2. **Automate everything**

Manual is fragile
Automation is documentation that runs
If you do it twice, automate it

### 3. **Design for failure**

Everything fails eventually
Failures should be isolated
Recovery should be automatic

### 4. **Data-Driven decision making**

Technical decisions are based on objective criteria, measurements, and evidence rather than opinions or assumptions.

**What this means:**
- Define success metrics before making decisions
- Measure and monitor what matters (key iindicators)
- Use Architecture Decision Records (ADRs) to document reasoning
- Regular retrospectives and continuous improvement
- Metrics inform architecture

**Example:** Choose technologies based on performance benchmarks, team expertise, and total cost of ownership rather than popularity or personal preference.


### 3. **Production first & shift-left; quality, security and reliability are everyone's responsibility**

Quality, security, and reliability are built into every stage of development, not added as afterthoughts.

Code that works in production > Code that works on your laptop
Observability is not optional
Security is built in, not bolted on


**What this means:**
- Shift-left testing and security
- Code reviews are mandatory
- Automated quality gates in CI/CD
- Shared ownership of production issues

**Example:** Developers write tests, perform security scans, and monitor production metrics as part of their daily work.

### 4. **Simplicity Over Complexity**

Favor simple, maintainable solutions over clever or overly complex ones. The best code is code that doesn't need to be written.

**What this means:**
- Simple systems are maintainable
- Complexity is technical debt
- YAGNI (You Aren't Gonna Need It) principle - avoid building features early
- Avoid premature optimization
- Refactor continuously as real needs emerge.
- Delete unused code and features
- Prefer boring, proven technology

**Example:** Use existing libraries and frameworks rather than building custom solutions unless there's a clear, documented business need.


### 5. **Living Documentation Through Code Intelligence**

Documentation is automatically generated from code and kept up-to-date through intelligent tooling, reducing manual documentation burden while ensuring accuracy.

**What this means:**
- API documentation generated from code annotations (OpenAPI, JSDoc, Swagger)
- Code intelligence tools (like Google's CodeWiki) that automatically create and maintain documentation
- Inline code comments for complex logic, automatically surfaced in documentation
- Architecture Decision Records (ADRs) for significant decisions, integrated with code repositories
- README files for getting started, minimal but essential

**Example:** API endpoints are documented using OpenAPI annotations in the code. Tools like CodeWiki automatically generate browsable documentation showing usage examples, dependencies, and ownership. When code changes, documentation updates automatically.

**Tools and Approaches:**
- **Code Intelligence Platforms:** Google CodeWiki, Sourcegraph, GitHub Copilot Docs
- **API Documentation:** Swagger/OpenAPI auto-generation, GraphQL introspection
- **Code Annotations:** JSDoc, JavaDoc, Python docstrings that feed into doc generators
- **Architectural Context:** Tools that visualize service dependencies and data flows from code
- **Living Runbooks:** Generated from infrastructure as code and deployment configurations

**What to Document Manually:**
- Architecture Decision Records (ADRs) for why decisions were made
- Getting started guides and onboarding documentation
- High-level system architecture and design philosophy
- Domain knowledge and business context not evident in code

### 6. **Continuous learning and improvement**

Engineering practices evolve based on lessons learned, industry trends, and team feedback.

**What this means:**
- Regular retrospectives and post-mortems
- Experimentation and innovation time
- Sharing knowledge through documentation and presentations
- Updating standards based on real-world experience

**Example:** After a production incident, the team conducts a blameless post-mortem and updates standards or practices to prevent recurrence.
