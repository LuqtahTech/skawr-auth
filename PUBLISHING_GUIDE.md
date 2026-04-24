# Skawr Shared Authentication Publishing Guide

This guide provides instructions for publishing the shared authentication packages to package registries.

## Overview

The Skawr shared authentication system consists of two packages:

1. **Backend Package**: `skawr-auth` (Python/PyPI)
2. **Frontend Package**: `@skawr/auth-frontend` (Node.js/npm)

## Prerequisites

### For Python Package (PyPI)
- Python 3.9+
- `build` and `twine` packages
- PyPI account with publishing permissions
- API token for PyPI authentication

### For Node.js Package (npm)
- Node.js 18+
- npm account with publishing permissions
- npm authentication token

## Backend Package Publishing (skawr-auth)

### 1. Prepare the Package

Navigate to the backend directory:
```bash
cd /path/to/skawr-auth/backend
```

### 2. Install Build Tools

```bash
# Install build dependencies
pip install build twine

# Or use pipx (recommended)
pipx install build
pipx install twine
```

### 3. Update Version (if needed)

Update the version in `pyproject.toml`:
```toml
[project]
name = "skawr-auth"
version = "0.1.1"  # Update version
```

### 4. Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build source distribution and wheel
python -m build
```

This creates:
- `dist/skawr_auth-0.1.0.tar.gz` (source distribution)
- `dist/skawr_auth-0.1.0-py3-none-any.whl` (wheel)

### 5. Test the Build

```bash
# Install locally to test
pip install dist/skawr_auth-0.1.0-py3-none-any.whl

# Or test with editable install
pip install -e .
```

### 6. Upload to PyPI

```bash
# Upload to Test PyPI first (recommended)
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Upload to production PyPI
twine upload dist/*
```

### 7. Verify Publication

```bash
# Install from PyPI to verify
pip install skawr-auth==0.1.0

# Test import
python -c "import skawr_auth; print('✓ Package installed successfully')"
```

## Frontend Package Publishing (@skawr/auth-frontend)

### 1. Prepare the Package

Navigate to the frontend directory:
```bash
cd /path/to/skawr-auth/frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Update Version (if needed)

Update the version in `package.json`:
```json
{
  "name": "@skawr/auth-frontend",
  "version": "0.1.1"
}
```

### 4. Build the Package

```bash
# Clean previous builds
npm run clean

# Build TypeScript to JavaScript
npm run build
```

This creates the `dist/` directory with:
- `index.js` (main entry point)
- `index.d.ts` (TypeScript definitions)
- Component files and utilities

### 5. Test the Build

```bash
# Run tests
npm test

# Link locally for testing
npm link

# In another project
npm link @skawr/auth-frontend
```

### 6. Login to npm

```bash
# Login to npm
npm login

# Verify login
npm whoami
```

### 7. Publish to npm

```bash
# Publish to npm registry
npm publish

# For scoped packages, ensure it's public
npm publish --access public
```

### 8. Verify Publication

```bash
# Install from npm to verify
npm install @skawr/auth-frontend@0.1.0

# Check package info
npm info @skawr/auth-frontend
```

## Automated Publishing (CI/CD)

### GitHub Actions Example

Create `.github/workflows/publish.yml`:

```yaml
name: Publish Packages

on:
  push:
    tags:
      - 'v*'

jobs:
  publish-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        working-directory: ./backend
        run: python -m build

      - name: Publish to PyPI
        working-directory: ./backend
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*

  publish-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Build package
        working-directory: ./frontend
        run: npm run build

      - name: Publish to npm
        working-directory: ./frontend
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: npm publish --access public
```

## Version Management

### Semantic Versioning

Follow semantic versioning (semver):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

### Release Process

1. **Update Changelogs**: Document changes in `CHANGELOG.md`
2. **Version Bump**: Update version in both packages
3. **Test**: Ensure all tests pass
4. **Tag Release**: Create git tag `git tag v0.1.0`
5. **Publish**: Run publishing commands or trigger CI/CD
6. **Verify**: Test installation from registries

## Package Configuration

### Python Package (pyproject.toml)

```toml
[project]
name = "skawr-auth"
version = "0.1.0"
description = "Shared authentication and API key management for Skawr projects"
readme = "README.md"
authors = [
    {name = "Skawr Team", email = "tech@skawr.com"}
]
license = {text = "MIT"}
keywords = ["skawr", "auth", "fastapi", "sqlalchemy"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Framework :: FastAPI",
]

[project.urls]
Homepage = "https://github.com/skawr/skawr-auth"
Repository = "https://github.com/skawr/skawr-auth"
Documentation = "https://github.com/skawr/skawr-auth/blob/main/README.md"
```

### Node.js Package (package.json)

```json
{
  "name": "@skawr/auth-frontend",
  "version": "0.1.0",
  "description": "Shared frontend authentication components for Skawr projects",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "repository": {
    "type": "git",
    "url": "https://github.com/skawr/skawr-auth.git",
    "directory": "frontend"
  },
  "homepage": "https://github.com/skawr/skawr-auth",
  "bugs": {
    "url": "https://github.com/skawr/skawr-auth/issues"
  },
  "keywords": ["skawr", "auth", "react", "typescript", "frontend"],
  "license": "MIT"
}
```

## Security Considerations

### API Tokens
- Store tokens securely (environment variables, secret managers)
- Use token rotation for long-term projects
- Limit token permissions (publish-only)

### Package Signing
- Consider signing packages for integrity verification
- Use trusted publishing with OIDC when available

### Vulnerability Scanning
- Enable security scanning in CI/CD
- Monitor for security advisories
- Keep dependencies updated

## Troubleshooting

### Common Python Publishing Issues

**Issue**: `ERROR: Repository 'https://upload.pypi.org/legacy/' is not a valid repository`
**Solution**: Check PyPI URL and credentials

**Issue**: `ERROR: File already exists`
**Solution**: Increment version number

### Common npm Publishing Issues

**Issue**: `npm ERR! 403 Forbidden`
**Solution**: Check npm authentication and package permissions

**Issue**: `npm ERR! Package name too similar`
**Solution**: Choose a different package name

## Post-Publishing Tasks

1. **Update Documentation**: Update installation instructions
2. **Notify Teams**: Inform development teams of new versions
3. **Monitor Downloads**: Track package adoption
4. **Gather Feedback**: Collect user feedback for improvements

## Package URLs

After publishing, packages will be available at:

- **PyPI**: https://pypi.org/project/skawr-auth/
- **npm**: https://www.npmjs.com/package/@skawr/auth-frontend

## Support

For publishing issues:
1. Check package registry status pages
2. Review package configurations
3. Verify authentication credentials
4. Contact package registry support if needed

---

*Last Updated: April 2026*
*Version: 1.0*