# mypylogger Security

**Security posture and vulnerability management**

## Current Security Status

**Last Scan**: 2025-10-27
**Active Findings**: 3 Medium severity
**Runtime Dependencies**: 0
**Development Dependencies**: Regularly audited

### Severity Breakdown

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0 | ✅ None |
| High | 0 | ✅ None |
| **Medium** | **3** | ⚠️ Dev dependencies only |
| Low | 0 | ✅ None |

### Current Findings Summary

All 3 medium-severity findings are in **development/build dependencies only**, not in the runtime library:

1. **pip 25.2** - Path traversal in sdist extraction (GHSA-4xh5-x5gv-qwph)
   - Affects: Development tooling
   - Impact: None for end users
   - Workaround: Avoid installing untrusted sdist packages
   - Planned fix: Upgrade to pip 25.3 when available (2025-11-15)

2. **py 1.11.0** - ReDoS vulnerability in Subversion parsing (PYSEC-2022-42969)
   - Affects: Testing infrastructure (pytest dependency)
   - Impact: None for end users
   - Status: No fix available, monitoring upstream

3. **setuptools 75.3.2** - Path traversal in PackageIndex (PYSEC-2025-49)
   - Affects: Build tooling
   - Impact: None for end users
   - Fix available: setuptools 78.1.1

**Detailed findings**: [security/findings/SECURITY_FINDINGS.md](../security/findings/SECURITY_FINDINGS.md)

## Security Guarantees

### What mypylogger DOES Provide

✅ **Zero runtime dependencies**
- No third-party code in production
- Pure Python standard library only
- Reduces supply chain attack surface to zero

✅ **Graceful error handling**
- Never crashes the host application
- Fails safely to plain text if JSON serialization fails
- Errors logged to stderr without propagation

✅ **Safe defaults**
- No network requests
- No code execution from configuration
- No file writes unless explicitly enabled via `LOG_TO_FILE`
- Protected standard fields cannot be overridden

✅ **Input validation**
- Log levels validated against safe list
- File paths validated before use
- Non-serializable data skipped gracefully
- Environment variables sanitized

✅ **Stack frame safety**
- Maximum frame inspection limit (20 frames)
- Graceful fallback if inspection fails
- No infinite loops in source location tracking

✅ **Minimal privilege requirements**
- Runs with standard user permissions
- Only requires write access if file logging enabled
- No administrative/root privileges needed

### What mypylogger Does NOT Guarantee

❌ **Log data encryption** - Logs are plain JSON text
❌ **PII/secret detection** - You must sanitize sensitive data before logging
❌ **Log tampering protection** - Use external log integrity tools
❌ **Rate limiting** - Application must handle log volume
❌ **Authentication/authorization** - For file access, relies on OS permissions
❌ **GDPR/compliance features** - Application must manage compliance
❌ **Log retention policies** - Use external tools for rotation/cleanup

## Security Best Practices

### 1. Never Log Sensitive Data

```python
# ❌ BAD - Logs credentials
logger.info("User login", extra={"password": user_password})

# ✅ GOOD - Logs only identifiers
logger.info("User login", extra={"user_id": user_id})
```

### 2. Sanitize User Input

```python
# ❌ BAD - Logs raw user input
logger.info(f"Search query: {request.GET['q']}")

# ✅ GOOD - Sanitizes/validates first
safe_query = sanitize_input(request.GET['q'])
logger.info("Search performed", extra={"query": safe_query})
```

### 3. Secure File Logging

```python
# ✅ GOOD - Explicit permissions
os.environ["LOG_FILE_DIR"] = "/var/log/myapp"  # Restricted directory
os.makedirs("/var/log/myapp", mode=0o750, exist_ok=True)
```

### 4. Validate Environment Variables

```python
# ✅ GOOD - Validate before use
import os
log_dir = os.getenv("LOG_FILE_DIR", "/tmp")
if not os.path.isdir(log_dir):
    raise ValueError(f"Invalid log directory: {log_dir}")
```

### 5. Limit Log Volume

```python
# ✅ GOOD - Rate limit expensive operations
from functools import lru_cache
import time

@lru_cache(maxsize=1)
def get_rate_limited_logger(timestamp_window: int):
    """Returns logger, cached per time window"""
    return get_logger(__name__)

# Logs at most once per second
logger = get_rate_limited_logger(int(time.time()))
logger.info("High-frequency event")
```

## Vulnerability Management

### Reporting Security Issues

**Do NOT** open public GitHub issues for security vulnerabilities.

**Email**: admin@bittikens.com
**Subject**: [SECURITY] mypylogger vulnerability report

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Response time**: Within 72 hours

### Security Scanning

mypylogger uses automated security scanning:

- **bandit** - Python security linting
- **pip-audit** - Dependency vulnerability scanning
- **ruff** - Code quality and security rules
- **mypy** - Type safety checking

**Scan frequency**: Every commit via CI/CD

### Dependency Updates

- Development dependencies reviewed monthly
- Security patches applied within 7 days of disclosure
- Breaking changes evaluated before upgrade

### Security Advisories

Subscribe to security updates:
- Watch the GitHub repository
- Check [SECURITY_FINDINGS.md](../security/findings/SECURITY_FINDINGS.md) for current status

## Threat Model

### In Scope

✅ Vulnerabilities in mypylogger source code
✅ Malicious input causing crashes or unexpected behavior
✅ Information disclosure via logs
✅ Dependency vulnerabilities affecting end users

### Out of Scope

❌ Log data security after writing (application responsibility)
❌ OS-level file permission issues
❌ Network transport security (not applicable - no network code)
❌ Misuse of logging API by application developers
❌ Performance/availability issues (not security vulnerabilities)

## Compliance Notes

mypylogger is a **logging utility**, not a compliance solution.

### GDPR Considerations

- **PII Logging**: Application must prevent logging PII
- **Right to Erasure**: Application must manage log retention/deletion
- **Data Minimization**: Use structured logging to limit data capture

### SOC 2 / ISO 27001

- **Audit Trails**: JSON logs provide structured audit data
- **Log Integrity**: Use external tools for tamper protection
- **Access Control**: Rely on OS file permissions

### HIPAA

- **PHI Protection**: Never log protected health information
- **Audit Logging**: Structured logs suitable for audit trails
- **Encryption**: Use disk encryption for log files

## Security Philosophy

mypylogger's security approach:

1. **Minimal surface area** - Fewer features = fewer vulnerabilities
2. **Zero dependencies** - No supply chain risk for runtime
3. **Safe defaults** - Secure by default, opt-in for risky features
4. **Graceful degradation** - Errors don't cascade to host application
5. **Transparency** - Open source, auditable code

**Lines of code**: ~759 (easy to audit)
**External dependencies**: 0 (runtime)
**Network code**: 0 lines
**Filesystem writes**: Optional, explicit opt-in only

---

**Detailed findings**: [security/findings/SECURITY_FINDINGS.md](../security/findings/SECURITY_FINDINGS.md)
**Changelog**: [security/findings/history/findings-changelog.md](../security/findings/history/findings-changelog.md)

**Next:** [PERFORMANCE.md](PERFORMANCE.md) | [Back to docs](README.md)
