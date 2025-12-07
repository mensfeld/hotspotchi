# Contributing to HotSpotchi

Thank you for your interest in contributing to HotSpotchi! This document provides guidelines for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title describing the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Raspberry Pi model, OS version, Python version)

### Suggesting Features

1. Check existing issues and discussions
2. Create a new issue with:
   - Clear description of the feature
   - Use case / why it would be useful
   - Any implementation ideas

### Adding New Characters or SSIDs

If you discover new character byte combinations or special SSIDs:

1. Verify the information (test it yourself if possible)
2. Add entries to `src/hotspotchi/characters.py`
3. Add validation tests to `tests/test_characters.py`
4. Include source/verification info in your PR description

### Code Contributions

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Run tests and linting:
   ```bash
   pytest
   ruff check src/ tests/
   ruff format src/ tests/
   mypy src/hotspotchi
   ```
5. Commit with clear messages:
   ```bash
   git commit -m "feat: add new feature description"
   ```
6. Push and create a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hotspotchi.git
cd hotspotchi

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions/classes
- Keep functions focused and small
- Use meaningful variable names

We use `ruff` for linting and formatting. Run before committing:

```bash
ruff check --fix .
ruff format .
```

## Testing

- Write tests for new features
- Maintain or improve test coverage
- Tests should be in `tests/` directory
- Use pytest fixtures from `conftest.py`

Run tests:
```bash
pytest                              # Run all tests
pytest tests/test_selection.py      # Run specific file
pytest -v                           # Verbose output
pytest --cov=hotspotchi            # With coverage
```

## Commit Messages

Use conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for seasonal character filtering
fix: correct MAC address formatting for bytes > 127
docs: update installation instructions for Pi 5
test: add tests for cycle mode wraparound
```

## Pull Request Process

1. Update README.md if adding user-facing features
2. Update docstrings for new/changed functions
3. Ensure all tests pass
4. Ensure linting passes
5. Request review from maintainers

## Questions?

Feel free to open an issue for any questions about contributing!
