# Changelog

All notable changes to this project will be documented in this file.

## [v1.0.0-rc.1] - 2025-01-01

### Added
- **QA Suite**: Comprehensive frontend, backend, and static analysis testing
- **GitHub Actions CI**: Automated QA on every push and pull request
- **Runtime Configuration**: Dynamic API base configuration via runtime-config.js
- **Centralized API Handling**: apiFetch wrapper for consistent API calls
- **Local Regression Runners**: One-command testing for bash and PowerShell

### Changed
- **CORS Hardening**: Specific header allowlists and credentials support
- **Script Loading Order**: runtime-config.js now loads before any other scripts
- **HTML Structure**: Standardized head section ordering across all pages
- **API Architecture**: Replaced direct fetch calls with centralized apiFetch wrapper

### Security
- **CSP Headers**: Content Security Policy via vercel.json
- **CORS Configuration**: Restricted origins and specific header allowlists
- **Runtime Injection**: API base configuration injected at deployment time

### Technical Debt
- **Code Deduplication**: Removed duplicate runtime-config.js includes
- **Script Ordering**: Fixed potential race conditions in script loading
- **False Positive Elimination**: Refined QA scripts to exclude dependencies

### Infrastructure
- **CI/CD Pipeline**: GitHub Actions workflow for continuous quality assurance
- **Local Testing**: Cross-platform regression testing scripts
- **Documentation**: Comprehensive README with setup and testing instructions

## [v0.9.0] - 2024-12-01

### Added
- Initial PF Creative AI Studio implementation
- Multi-language support (English, Bahasa Malaysia, 中文)
- Basic authentication and user management
- Admin activity logging and monitoring
