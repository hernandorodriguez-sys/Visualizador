# Contributing to ECG Monitor Visualizer

Thank you for your interest in contributing to the ECG Monitor Visualizer project! We welcome contributions from the community.

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the Issues section
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)

### Feature Requests

1. Check existing issues for similar requests
2. Create a new issue with:
   - Clear description of the proposed feature
   - Use case and benefits
   - Implementation suggestions if any

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the coding standards
4. Add tests for new functionality
5. Update documentation if needed
6. Commit with clear, descriptive messages
7. Push to your fork
8. Create a Pull Request

## Development Setup

1. Clone the repository
2. Install dependencies: `uv sync`
3. Run tests: `python -m pytest tests/`
4. Make your changes
5. Run tests again to ensure nothing is broken

## Coding Standards

### Python Style

- Follow PEP 8 conventions
- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black formatter default)
- Use type hints where possible
- Add docstrings to all functions, classes, and modules

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in imperative mood (e.g., "Add", "Fix", "Update")
- Keep the first line under 50 characters
- Add detailed description if needed

### Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for good test coverage
- Use descriptive test names

### Documentation

- Update README.md for significant changes
- Add docstrings to new functions/classes
- Update API documentation in docs/api.md

## Project Structure

```
visualizador/
├── src/visualizador/     # Main package
├── tests/               # Unit tests
├── docs/                # Documentation
├── main.py             # Entry point
└── pyproject.toml      # Project configuration
```

## Areas for Contribution

- Signal processing algorithms
- GUI improvements
- Hardware integration
- Performance optimization
- Documentation
- Testing

## Getting Help

- Check the README.md for setup and usage instructions
- Look at existing issues and PRs
- Ask questions in discussions

Thank you for contributing!