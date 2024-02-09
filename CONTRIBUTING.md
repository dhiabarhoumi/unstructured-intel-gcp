# Contributing to Unstructured Intelligence Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/yourhandle/unstructured-intel-gcp.git
cd unstructured-intel-gcp
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Code Style

We use:
- **black** for code formatting
- **ruff** for linting
- **mypy** for type checking

Run before committing:
```bash
make format
make lint
```

## Testing

Write tests for all new features:
```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Commit Messages

Follow Conventional Commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation only
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance

Examples:
```
feat: add Wikipedia trending analysis
fix: correct embedding dimension calculation
docs: update deployment guide
```

## Pull Request Process

1. Create a feature branch:
```bash
git checkout -b feat/my-feature
```

2. Make your changes and commit:
```bash
git add .
git commit -m "feat: add my feature"
```

3. Push to your fork:
```bash
git push origin feat/my-feature
```

4. Open a Pull Request with:
   - Clear description of changes
   - Test coverage
   - Documentation updates

## Code Review

All submissions require review. We look for:
- Code quality and style
- Test coverage (> 80%)
- Documentation
- Performance impact
- Security considerations

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Documentation improvements
- Questions about the codebase

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
