# Implementation Checklists

Consolidated checklists for service implementation, platform setup, operational readiness, and compliance.

---

## Service-Level Checklist

Use this checklist when building or reviewing a microservice.

### Architecture & Design
- [ ] Domain model free of framework dependencies
- [ ] Clear bounded context defined with ubiquitous language
- [ ] Hexagonal architecture implemented (ports/adapters)
- [ ] API versioning strategy implemented
- [ ] OpenAPI/Swagger specification available
- [ ] Event schema defined and registered

### Code Quality
- [ ] Comprehensive test coverage (>80%)
- [ ] Unit tests for all business logic
- [ ] Integration tests for external boundaries
- [ ] Contract tests for API consumers
- [ ] No critical or high severity vulnerabilities
- [ ] Code review completed

### Resilience
- [ ] All external calls protected with circuit breakers
- [ ] Retry policies with exponential backoff configured
- [ ] Timeouts defined for all network calls
- [ ] Bulkhead isolation for critical paths
- [ ] Fallback behavior implemented
- [ ] Graceful shutdown implemented

### Observability
- [ ] Distributed tracing implemented (OpenTelemetry)
- [ ] Structured logging with correlation IDs
- [ ] Custom business metrics defined
- [ ] Health checks configured (liveness/readiness)
- [ ] Prometheus metrics exposed
- [ ] Dashboard created for service

### Security
- [ ] Authentication implemented (OAuth2/JWT)
- [ ] Authorization rules defined
- [ ] Input validation on all endpoints
- [ ] Secrets externalized (not in code/config)
- [ ] OWASP dependency check passing
- [ ] Security headers configured

### Data
- [ ] Database migrations automated (Flyway/Liquibase)
- [ ] Connection pooling configured
- [ ] Indexes defined for common queries
- [ ] Backup and restore tested

### Configuration
- [ ] Environment-specific configuration separated
- [ ] All configuration externalized
- [ ] Feature flags for new functionality
- [ ] Rate limiting implemented

### Documentation
- [ ] README with setup instructions
- [ ] API documentation up to date
- [ ] Architecture decision records (ADRs)
- [ ] Runbooks for common issues

---

## Platform-Level Checklist

Use this checklist when setting up or reviewing platform infrastructure.

### Service Mesh & Networking
- [ ] Service mesh deployed (Istio/Linkerd/Cilium)
- [ ] mTLS enabled for all service communication
- [ ] NetworkPolicy restricting pod traffic
- [ ] Ingress/egress gateways configured
- [ ] Traffic management policies defined

### API Gateway
- [ ] API Gateway deployed and configured
- [ ] Rate limiting enabled at edge
- [ ] Authentication at gateway level
- [ ] Request routing configured
- [ ] API versioning supported

### Secrets Management
- [ ] External secret management configured (Vault/cloud)
- [ ] Secret rotation policies defined
- [ ] No secrets in source control
- [ ] Audit logging for secret access
- [ ] PKI/certificate management automated

### GitOps & Deployment
- [ ] GitOps workflow established (ArgoCD/Flux)
- [ ] Deployment manifests in version control
- [ ] Environment promotion workflow defined
- [ ] Rollback strategy documented and tested
- [ ] Canary/blue-green deployment configured

### Kubernetes Configuration
- [ ] PodDisruptionBudget configured for all services
- [ ] Resource requests and limits defined
- [ ] Topology spread constraints for zone HA
- [ ] Pod security policies/standards enforced
- [ ] Container image tags (no `latest` in production)

### Event Infrastructure
- [ ] Message broker deployed and configured
- [ ] Schema registry operational
- [ ] Dead-letter queues configured
- [ ] Idempotent consumers implemented
- [ ] Event retention policies defined

### Database
- [ ] Primary/replica configuration for HA
- [ ] Connection failover tested
- [ ] Backup automation verified
- [ ] Point-in-time recovery tested
- [ ] Performance monitoring enabled

### Multi-Tenancy (if applicable)
- [ ] Tenant isolation strategy implemented
- [ ] Tenant context propagation working
- [ ] Resource quotas per tenant configured
- [ ] Tenant-aware caching implemented

---

## Operational Readiness Checklist

Use this checklist before promoting to production.

### Disaster Recovery
- [ ] RTO/RPO requirements documented
- [ ] Disaster recovery plan documented
- [ ] Backup and restore tested (within 90 days)
- [ ] Cross-region replication configured (if required)
- [ ] Failover procedures documented and tested

### Chaos Engineering
- [ ] Chaos experiments defined
- [ ] Initial chaos testing completed
- [ ] Game day schedule established
- [ ] Findings documented and addressed

### Observability
- [ ] SLIs defined for all critical paths
- [ ] SLOs established and documented
- [ ] Error budgets calculated
- [ ] Alerting rules configured
- [ ] Runbooks linked to all alerts
- [ ] Dashboards operational and accurate
- [ ] On-call rotation configured

### Performance
- [ ] Load testing completed
- [ ] Performance baseline established
- [ ] Auto-scaling configured and tested
- [ ] Resource limits validated under load

### Cost
- [ ] Cost monitoring configured
- [ ] Cost alerts defined
- [ ] Resource right-sizing review completed
- [ ] Spot/preemptible instances evaluated

### Documentation
- [ ] Architecture documentation complete
- [ ] Runbooks for all alerts
- [ ] Incident response procedures
- [ ] Escalation paths defined
- [ ] Contact information current

---

## Security & Compliance Checklist

Use this checklist for security review and compliance validation.

### Access Control
- [ ] Least privilege enforced
- [ ] Service accounts with minimal permissions
- [ ] Role-based access control (RBAC) configured
- [ ] No shared credentials
- [ ] Access review completed (quarterly)

### Supply Chain Security
- [ ] Container images signed and verified
- [ ] SBOM generated for all releases
- [ ] Base images from trusted sources
- [ ] Dependency vulnerability scan passing
- [ ] No critical/high CVEs in production

### Policy Enforcement
- [ ] Policy-as-code implemented (OPA/Kyverno)
- [ ] Admission controllers configured
- [ ] Network policies enforced
- [ ] Pod security standards applied

### Audit & Compliance
- [ ] Audit logging enabled
- [ ] Log retention meets compliance requirements
- [ ] Data classification completed
- [ ] PII handling validated
- [ ] Encryption at rest verified
- [ ] Encryption in transit verified

### Security Testing
- [ ] SAST (static analysis) in CI/CD
- [ ] DAST (dynamic analysis) completed
- [ ] Penetration testing completed (annually)
- [ ] Security review documented

---

## Pre-Production Deployment Checklist

Use this checklist before each production deployment.

### Code Readiness
- [ ] All tests passing
- [ ] Code review approved
- [ ] Security scan passing
- [ ] No blocking issues

### Deployment Readiness
- [ ] Deployment plan documented
- [ ] Rollback plan documented
- [ ] Feature flags configured
- [ ] Database migrations tested

### Monitoring Readiness
- [ ] Dashboards updated
- [ ] Alert thresholds reviewed
- [ ] On-call notified
- [ ] Runbooks current

### Communication
- [ ] Stakeholders notified
- [ ] Change record created
- [ ] Maintenance window scheduled (if needed)

---

## Post-Incident Checklist

Use this checklist after resolving an incident.

### Immediate
- [ ] Incident resolved and verified
- [ ] Customer communication sent
- [ ] Incident timeline documented

### Within 24 Hours
- [ ] Incident report drafted
- [ ] Root cause identified
- [ ] Immediate fixes deployed

### Within 1 Week
- [ ] Blameless post-mortem completed
- [ ] Action items created and assigned
- [ ] Runbooks updated
- [ ] Alerts/monitoring improved
- [ ] Knowledge shared with team

### Within 1 Month
- [ ] Preventive measures implemented
- [ ] Chaos experiments updated
- [ ] Documentation updated
- [ ] Lessons learned shared
