# Contributing to ComfyUI-3D-Pack

Thank you for your interest in contributing to ComfyUI-3D-Pack! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- CUDA-compatible GPU (recommended)
- Git
- Basic knowledge of 3D graphics and ML/AI

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/ComfyUI-3D-Pack.git
cd ComfyUI-3D-Pack
```

2. **Set up development environment**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

3. **Configure environment**

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Add your HuggingFace token, API keys, etc.
```

4. **Run tests**

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m security

# Run with coverage
pytest --cov=. --cov-report=html
```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/modifications

### Code Style

We use automated code formatting and linting tools:

- **Black** for code formatting (line length: 120)
- **Ruff** for linting and import sorting
- **mypy** for type checking
- **isort** for import organization

These tools run automatically via pre-commit hooks. You can also run them manually:

```bash
# Format code
black .

# Lint code
ruff check . --fix

# Type check
mypy .

# Sort imports
isort .
```

### Commit Messages

Follow the conventional commits specification:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/modifications
- `chore`: Maintenance tasks

Examples:
```
feat(webserver): add API key authentication
fix(security): prevent path traversal vulnerability
docs(readme): update installation instructions
test(config): add tests for configuration loading
```

### Testing Requirements

All contributions must include appropriate tests:

1. **Unit Tests** - Test individual functions/classes
2. **Integration Tests** - Test component interactions
3. **Security Tests** - Test security features (if applicable)

Minimum coverage: 80% for new code

```bash
# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Documentation

- Add docstrings to all public functions/classes (Google style)
- Update README.md if adding new features
- Add inline comments for complex logic
- Update ARCHITECTURE.md for architectural changes

Example docstring:
```python
def process_mesh(mesh_path: str, optimize: bool = True) -> Mesh:
    """
    Process and optimize a 3D mesh.

    Args:
        mesh_path: Path to the mesh file
        optimize: Whether to optimize the mesh geometry

    Returns:
        Processed Mesh object

    Raises:
        FileNotFoundError: If mesh file doesn't exist
        ValueError: If mesh format is invalid
    """
```

## Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
   - Write code following our style guide
   - Add/update tests
   - Update documentation

3. **Run quality checks**

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Run tests
pytest

# Check coverage
pytest --cov=. --cov-report=term-missing
```

4. **Commit your changes**

```bash
git add .
git commit -m "feat: add awesome feature"
```

5. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

6. **Create Pull Request**
   - Go to GitHub and create a PR
   - Fill out the PR template
   - Link related issues
   - Request review from maintainers

### PR Requirements

- ✅ All tests pass
- ✅ Code coverage ≥ 80%
- ✅ No linting errors
- ✅ Documentation updated
- ✅ Commits follow conventional commits
- ✅ PR description is clear and complete

### Review Process

1. Automated checks run (CI/CD)
2. Code review by maintainers
3. Address feedback
4. Approval and merge

## Security Vulnerabilities

**DO NOT** create public issues for security vulnerabilities.

Instead:
1. Email security concerns to the maintainers
2. Include details of the vulnerability
3. Allow time for a fix before public disclosure

## Adding New 3D Models

To add support for a new 3D generation model:

1. Create a new module in `Gen_3D_Modules/YourModel/`
2. Implement the model interface
3. Add configuration in `Checkpoints/`
4. Write comprehensive tests
5. Update documentation
6. Add example workflows

See `ARCHITECTURE.md` for detailed guidelines.

## Performance Optimization

When contributing performance improvements:

1. **Benchmark** - Provide before/after benchmarks
2. **Profile** - Use profiling tools to identify bottlenecks
3. **Document** - Explain the optimization technique
4. **Test** - Ensure no functionality regression

## Questions?

- **GitHub Discussions** - For general questions
- **GitHub Issues** - For bugs and feature requests
- **Discord** - For real-time chat (if available)

## Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

Thank you for contributing to ComfyUI-3D-Pack! 🎉
