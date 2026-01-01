# Security Policy

## Supported Versions

The following versions receive security updates:

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Yes |
| < 1.0   | ❌ No |

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, report them via:

1. **Email:** security@racestrategy.dev
2. **Subject:** [SECURITY] Brief description

### What to Include

- Type of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

| Action | Timeline |
|--------|----------|
| Initial response | 48 hours |
| Assessment | 1 week |
| Fix development | 2-4 weeks |
| Public disclosure | After fix release |

---

## Security Features

### Authentication

- JWT tokens with configurable expiration
- API key authentication for services
- Role-based access control

### Data Protection

- Input validation via Pydantic
- SQL injection prevention (parameterized queries)
- XSS protection (React escaping)
- CORS configuration

### Network Security

- HTTPS/TLS encryption (production)
- Rate limiting
- Request size limits

---

## Security Best Practices

### Production Deployment

```env
# Required security settings
RSW_ENV=production
RSW_AUTH_ENABLED=true
JWT_SECRET=<strong-random-secret>
```

### Secret Management

- Never commit secrets to git
- Use environment variables or secret managers
- Rotate JWT secrets periodically

---

## Known Limitations

- Authentication is optional in development mode
- Rate limiting requires Redis
- Session data is cached (may be slightly stale)

---

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities.
