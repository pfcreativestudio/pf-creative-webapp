# PF Creative AI Studio

[![QA](https://github.com/yourusername/pf-creative-ai-studio/actions/workflows/qa.yml/badge.svg)](https://github.com/yourusername/pf-creative-ai-studio/actions/workflows/qa.yml)

Director-Grade AI for Film Production Scripts

## Overview

PF Creative AI Studio delivers production-ready script packages with professional cinematography controls and error-prevention technology. Go beyond prompts, get production-ready scripts.

## Features

- **Director-Grade AI**: Advanced system for complete, multi-scene script packages
- **Professional Cinematography Controls**: Built-in error-prevention technology
- **Multi-language Support**: English, Bahasa Malaysia, and 中文
- **Secure API Architecture**: Centralized apiFetch wrapper with runtime configuration

## Quick Start

### Local Development

1. **Setup Environment**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   npm install
   ```

2. **Run QA Suite**
   ```bash
   # One-command regression test
   bash ops/regress.sh
   
   # Or on Windows PowerShell
   powershell -ExecutionPolicy Bypass -File ops/regress.ps1
   ```

3. **Start Development Server**
   ```bash
   python main.py
   ```

### QA Commands

- **Frontend Checks**: `npm run qa:frontend`
- **Static QA**: `bash ops/qa_static.sh`
- **Backend Tests**: `pytest -q`
- **Hardcoded Scan**: `bash ops/scan-hardcoded.sh`

## Architecture

- **Frontend**: Modern HTML5 with Tailwind CSS, centralized API handling
- **Backend**: Python Flask with CORS hardening and security headers
- **Runtime Config**: Dynamic API base configuration via runtime-config.js
- **CI/CD**: Automated QA on every push/PR via GitHub Actions

## Security Features

- CORS hardening with specific header allowlists
- CSP headers via vercel.json
- Centralized apiFetch wrapper with credentials handling
- Runtime configuration injection for deployment flexibility

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure all QA checks pass: `bash ops/regress.sh`
4. Submit a pull request

## License

Proprietary - PF Creative AI Studio
