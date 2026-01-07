# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Please DO NOT open a public GitHub issue for security vulnerabilities.**

Instead, report security vulnerabilities by emailing:

**security@example.com**

Or use [GitHub's private vulnerability reporting](https://github.com/edarasumanth/autonomous-research-agent/security/advisories/new).

### What to Include

Please include the following information in your report:

- **Description**: A clear description of the vulnerability
- **Impact**: What could an attacker accomplish?
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Affected Versions**: Which versions are affected?
- **Possible Fix**: If you have suggestions for fixing the vulnerability

### What to Expect

1. **Acknowledgment**: We will acknowledge receipt within 48 hours
2. **Assessment**: We will assess the vulnerability and determine its severity
3. **Updates**: We will keep you informed of our progress
4. **Resolution**: We aim to resolve critical vulnerabilities within 7 days
5. **Credit**: With your permission, we will credit you in the security advisory

### Security Best Practices for Users

#### API Keys

- **Never commit API keys** to version control
- Use environment variables or `.env` files (excluded from git)
- Rotate keys periodically
- Use separate keys for development and production

#### Deployment

- Keep Docker images updated
- Run containers with minimal privileges
- Use HTTPS in production
- Restrict network access to the application

#### Dependencies

- Regularly update dependencies
- Monitor security advisories
- Use Dependabot alerts (enabled for this repository)

## Security Features

### Current Security Measures

- **Environment Variables**: Sensitive configuration via `.env` files
- **Docker Isolation**: Containerized deployment option
- **Dependency Scanning**: Dependabot alerts enabled
- **CI Security**: Automated security checks in CI pipeline

### Responsible Disclosure

We follow responsible disclosure practices:

1. Security issues are fixed before public disclosure
2. We coordinate disclosure timing with reporters
3. We publish security advisories for significant vulnerabilities
4. We credit reporters (with permission)

## Scope

### In Scope

- Application code vulnerabilities
- Authentication/authorization issues
- Data exposure risks
- Dependency vulnerabilities
- Docker security issues

### Out of Scope

- Vulnerabilities in third-party services (Anthropic, Tavily)
- Social engineering attacks
- Physical security
- Denial of service attacks

## Contact

For security-related questions or concerns:

- Email: security@example.com
- GitHub Security Advisories: [Report a vulnerability](https://github.com/edarasumanth/autonomous-research-agent/security/advisories/new)

Thank you for helping keep this project secure!
