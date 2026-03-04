# Security Policy

**[Documentation Index](DOCUMENTATION.md)** > Security

**Report Vulnerabilities:** [GitHub Security Advisories](https://github.com/19-84/chronicon/security/advisories/new)

---

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of chronicon seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please use GitHub Security Advisories:
- Navigate to: https://github.com/19-84/chronicon/security/advisories/new
- Or click the "Security" tab on the repository page

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Security Best Practices for Users

When using chronicon, we recommend following these security best practices:

### 1. Input Validation
- Only archive forums from trusted sources
- Verify forum URLs before archiving
- Be cautious when archiving user-generated content from unknown forums

### 2. File Permissions
- Archive outputs are created with default file permissions
- Ensure your output directory has appropriate permissions
- Be mindful of sensitive content when sharing archives

### 3. Rate Limiting
- Respect forum rate limits and terms of service
- Use the `--rate-limit` flag appropriately
- Some forums may block automated access

### 4. Data Privacy
- Archives contain user-generated content including usernames
- Be aware of privacy implications when publishing archives
- Consider GDPR and similar regulations if sharing archives publicly

### 5. Dependencies
- Keep chronicon up to date
- Regularly check for security updates: `uv pip list --outdated`
- Review dependency security advisories

### 6. Network Security
- Use HTTPS URLs for forums when possible
- Be cautious when archiving forums over untrusted networks
- Consider using a VPN if archiving sensitive forums

## Known Security Considerations

### User-Generated Content
Archives contain user-generated HTML content. While we process and sanitize content during export:
- HTML exports preserve post formatting
- Images are downloaded from external sources
- Links in posts may point to external resources

### Database Files
SQLite database files contain all archived content:
- Protect database files with appropriate permissions
- Database files are not encrypted
- Consider encrypting sensitive archives at rest

### Asset Downloads
When downloading images and assets:
- Files are downloaded from URLs in post content
- No size limits are enforced by default
- Malicious actors could reference very large files

## Security Update Process

1. Security vulnerabilities are assessed for severity
2. Patches are developed and tested
3. Security advisories are published
4. Fixed versions are released
5. Users are notified through GitHub releases

## Disclosure Policy

- We follow a coordinated disclosure process
- Security researchers are given credit for findings (if desired)
- We aim to fix critical vulnerabilities within 7 days
- Public disclosure occurs after patch release

## Contact

For security-related questions that are not vulnerabilities, you can:
- Open a GitHub Discussion
- Contact maintainers via GitHub

Thank you for helping keep chronicon and its users safe!

---

**See Also:**
- [examples/docker/SECURITY.md](examples/docker/SECURITY.md) - Docker security hardening
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Security-related troubleshooting
- [FAQ.md](FAQ.md) - Security FAQs

**Return to:** [Documentation Index](DOCUMENTATION.md)
