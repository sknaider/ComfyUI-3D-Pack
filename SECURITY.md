# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.6   | :white_check_mark: |
| < 0.1.6 | :x:                |

## Reporting a Vulnerability

**Please do NOT create public GitHub issues for security vulnerabilities.**

### How to Report

1. **Email**: Send details to the project maintainers (check CONTRIBUTING.md for contacts)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Update**: Weekly until resolved
- **Disclosure Timeline**: 90 days after fix is released

### Security Bug Bounty

We currently do not offer a bug bounty program, but we deeply appreciate security researchers who responsibly disclose vulnerabilities.

## Security Features

### Current Implementation

#### 1. Authentication & Authorization

- **API Key Authentication**: Bearer token and header-based authentication
- **IP Whitelisting**: Network-level access control
- **Path Validation**: Prevention of directory traversal attacks

#### 2. Secrets Management

- **Environment Variables**: Sensitive data stored in `.env` (not committed)
- **Key Hashing**: API keys hashed with SHA-256 before storage
- **No Hardcoded Secrets**: All secrets configurable via environment

#### 3. Input Validation

- **Path Sanitization**: All file paths validated and sanitized
- **File Extension Filtering**: Only allowed file types served
- **Request Validation**: Query parameters validated

#### 4. Dependency Security

- **Dependabot**: Automated dependency vulnerability scanning
- **Pinned Versions**: Critical dependencies pinned to known-good versions
- **Regular Updates**: Dependencies updated on weekly schedule

#### 5. Container Security

- **Non-root User**: Docker containers run as non-root (UID 1001)
- **Minimal Base**: Small attack surface
- **Health Checks**: Liveness and readiness probes
- **Resource Limits**: CPU and memory limits enforced

## Security Best Practices

### For Developers

1. **Code Reviews**: All code must be reviewed before merge
2. **Security Testing**: Run security tests with `pytest -m security`
3. **Static Analysis**: Use Bandit for security scanning
4. **Dependencies**: Keep dependencies up to date
5. **Secrets**: Never commit secrets to repository

### For Deployers

1. **Environment Variables**: Use `.env` for configuration
2. **API Keys**: Generate strong, unique API keys
3. **Network**: Deploy behind firewall/VPN
4. **Updates**: Apply security updates promptly
5. **Monitoring**: Enable audit logging and monitoring

### For Users

1. **Access Control**: Limit network access
2. **API Keys**: Rotate keys regularly
3. **Updates**: Keep software up to date
4. **Backups**: Regular backups of important data
5. **Monitoring**: Monitor for suspicious activity

## Known Security Considerations

### Current Limitations

1. **Rate Limiting**: Not yet implemented (planned for v0.2.0)
2. **Encryption**: No TLS/SSL termination (use reverse proxy)
3. **Audit Logging**: Basic logging only (enhanced logging in v0.2.0)
4. **Multi-tenancy**: Not fully isolated (enterprise v0.3.0)

### Recommended Deployment

```
Internet → CloudFlare → NGINX (TLS) → ComfyUI-3D-Pack
                         ↓
                    Rate Limiting
                    IP Filtering
                    DDoS Protection
```

## Security Checklist

Before deploying to production:

- [ ] Environment variables configured (not using defaults)
- [ ] Strong, unique API keys generated
- [ ] IP whitelist configured
- [ ] TLS/SSL enabled (via reverse proxy)
- [ ] Non-root user in containers
- [ ] Resource limits set
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Incident response plan documented
- [ ] Security scanning in CI/CD
- [ ] Secrets not in version control
- [ ] Dependencies up to date

## Secure Configuration Example

### .env (Production)

```bash
# Generate strong API keys
API_KEYS=$(python -c "import secrets; print(secrets.token_hex(32))")

# Restrict network access
ALLOWED_IPS=10.0.0.0/8

# Enable auth
ENABLE_AUTH=true

# Structured logging
LOG_FORMAT=json
LOG_LEVEL=INFO

# Secure HuggingFace token
HUGGINGFACE_TOKEN=hf_yourSecureTokenHere
```

### Docker Security

```yaml
# docker-compose.yml
services:
  comfyui-3d-pack:
    image: comfyui-3d-pack:latest
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    user: "1001:1001"
```

### Kubernetes Security

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: comfyui-3d-pack
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    fsGroup: 1001
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

## Vulnerability Disclosure Policy

We follow responsible disclosure:

1. **Report** vulnerability privately
2. **Acknowledge** within 48 hours
3. **Investigate** and develop fix
4. **Release** patched version
5. **Disclose** after 90 days or when fix is deployed

## Security Updates

Security updates are released as:

- **Critical**: Immediate hotfix release
- **High**: Release within 7 days
- **Medium**: Release in next minor version
- **Low**: Release in next major version

## Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

<!-- Will be updated as vulnerabilities are reported and fixed -->

## Contact

For security concerns, please contact:
- **Email**: See CONTRIBUTING.md for maintainer contacts
- **Response Time**: Within 48 hours

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Kubernetes Security](https://kubernetes.io/docs/concepts/security/)

---

**Last Updated**: 2025-11-16
**Version**: 0.1.6
