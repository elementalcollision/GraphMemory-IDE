# Contributing to GraphMemory-IDE

Thank you for your interest in contributing to GraphMemory-IDE! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/elementalcollision/GraphMemory-IDE.git
   cd GraphMemory-IDE
   ```
3. **Set up development environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Start development services**:
   ```bash
   cd docker
   docker compose up -d
   ```

## 📋 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Follow the coding standards outlined below
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. Test Your Changes

```bash
# Run Python tests
PYTHONPATH=. pytest server/ --maxfail=3 --disable-warnings -v

# Test Docker build
cd docker && docker compose build

# Validate documentation
./scripts/validate-docs.sh
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve issue description"
```

**Commit Message Format:**
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Reference to related issues
- Screenshots/examples if applicable

## 🎯 Areas for Contribution

### 🔧 Core Development
- **API Endpoints**: Enhance MCP server functionality
- **Database Operations**: Improve Kuzu GraphDB integration
- **Vector Search**: Optimize semantic search capabilities
- **Performance**: Improve query performance and caching

### 🐳 DevOps & Infrastructure
- **Docker Optimization**: Improve container builds and deployment
- **CI/CD**: Enhance GitHub Actions workflows
- **Monitoring**: Add observability and metrics
- **Security**: Implement authentication and authorization

### 📚 Documentation
- **API Documentation**: Improve endpoint documentation
- **Tutorials**: Create step-by-step guides
- **Examples**: Add more client examples
- **Troubleshooting**: Expand problem-solving guides

### 🧪 Testing
- **Unit Tests**: Increase test coverage
- **Integration Tests**: Add end-to-end testing
- **Performance Tests**: Add load and stress testing
- **Documentation Tests**: Validate examples work

### 🔌 IDE Integration
- **VS Code Plugin**: Develop IDE extension
- **IntelliJ Plugin**: Create JetBrains integration
- **Vim/Neovim**: Add editor support
- **Emacs**: Implement Emacs integration

## 📝 Coding Standards

### Python Code Style

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Add type annotations for all functions
- **Docstrings**: Document all public methods and classes
- **Line Length**: Maximum 88 characters (Black formatter)

```python
def process_telemetry_event(
    event: TelemetryEvent,
    user_id: Optional[str] = None
) -> ProcessingResult:
    """Process a telemetry event and store in database.
    
    Args:
        event: The telemetry event to process
        user_id: Optional user identifier for filtering
        
    Returns:
        ProcessingResult containing status and metadata
        
    Raises:
        ValidationError: If event data is invalid
        DatabaseError: If storage operation fails
    """
    # Implementation here
    pass
```

### Docker Best Practices

- **Multi-stage builds**: Use for production images
- **Non-root users**: Run containers as non-root
- **Layer optimization**: Minimize image layers
- **Security scanning**: Use Trivy for vulnerability checks

### Documentation Standards

- **Markdown**: Use consistent formatting
- **Examples**: Include working code examples
- **Cross-references**: Link related documentation
- **User-focused**: Write for your target audience

## 🧪 Testing Guidelines

### Test Structure

```
server/
├── test_main.py          # API endpoint tests
├── test_models.py        # Data model tests
├── test_database.py      # Database operation tests
└── test_integration.py   # Integration tests
```

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

def test_telemetry_ingest():
    """Test telemetry event ingestion."""
    event_data = {
        "event_type": "file_open",
        "timestamp": "2024-05-28T08:30:00Z",
        "user_id": "test-user",
        "data": {"file_path": "/test/file.py"}
    }
    
    response = client.post("/telemetry/ingest", json=event_data)
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Test Coverage

- **Minimum 90%**: Maintain high test coverage
- **Edge Cases**: Test error conditions and edge cases
- **Integration**: Test component interactions
- **Performance**: Include performance regression tests

## 📚 Documentation Guidelines

### README Files

Each component should have a comprehensive README:

- **Purpose**: What the component does
- **Setup**: How to install and configure
- **Usage**: Examples and common use cases
- **API**: Detailed endpoint/function documentation
- **Troubleshooting**: Common issues and solutions

### API Documentation

- **OpenAPI**: Use FastAPI's automatic documentation
- **Examples**: Include request/response examples
- **Error Codes**: Document all possible error responses
- **Client Libraries**: Provide usage examples

### Code Comments

```python
# Good: Explain why, not what
# Use exponential backoff to handle rate limiting
retry_delay = min(2 ** attempt, 60)

# Bad: Explain what the code does
# Set retry_delay to 2 raised to the power of attempt
retry_delay = 2 ** attempt
```

## 🔍 Code Review Process

### For Contributors

1. **Self-review**: Review your own changes first
2. **Test locally**: Ensure all tests pass
3. **Documentation**: Update relevant documentation
4. **Small PRs**: Keep pull requests focused and small

### For Reviewers

1. **Functionality**: Does the code work as intended?
2. **Tests**: Are there adequate tests?
3. **Documentation**: Is documentation updated?
4. **Style**: Does it follow project conventions?
5. **Security**: Are there any security concerns?

### Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests are included and pass
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered
- [ ] Backward compatibility maintained

## 🐛 Bug Reports

### Before Reporting

1. **Search existing issues**: Check if already reported
2. **Reproduce**: Ensure you can consistently reproduce
3. **Minimal example**: Create minimal reproduction case
4. **Environment**: Note your system details

### Bug Report Template

```markdown
## Bug Description
Brief description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.5]
- Docker: [e.g., 24.0.6]
- GraphMemory-IDE: [e.g., v1.0.0]

## Additional Context
Any other relevant information
```

## 💡 Feature Requests

### Before Requesting

1. **Check roadmap**: Review project roadmap and existing issues
2. **Use case**: Clearly define the problem you're solving
3. **Alternatives**: Consider existing solutions

### Feature Request Template

```markdown
## Feature Description
Clear description of the proposed feature

## Problem Statement
What problem does this solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
What other approaches did you consider?

## Additional Context
Any other relevant information
```

## 🏗️ Architecture Guidelines

### Adding New Endpoints

1. **RESTful design**: Follow REST principles
2. **Validation**: Use Pydantic models for validation
3. **Error handling**: Implement proper error responses
4. **Documentation**: Add OpenAPI documentation

### Database Changes

1. **Migration strategy**: Plan for schema changes
2. **Backward compatibility**: Maintain compatibility when possible
3. **Performance**: Consider query performance impact
4. **Testing**: Test with realistic data volumes

### Docker Changes

1. **Build optimization**: Minimize build time and image size
2. **Security**: Follow container security best practices
3. **Documentation**: Update deployment documentation
4. **Testing**: Test in CI/CD pipeline

## 🤝 Community Guidelines

### Code of Conduct

- **Be respectful**: Treat all contributors with respect
- **Be inclusive**: Welcome contributors from all backgrounds
- **Be constructive**: Provide helpful feedback
- **Be patient**: Remember that everyone is learning

### Communication

- **GitHub Issues**: For bugs and feature requests
- **Pull Requests**: For code discussions
- **Discussions**: For general questions and ideas

### Recognition

Contributors are recognized in:
- **README**: Major contributors listed
- **Releases**: Contributors mentioned in release notes
- **Documentation**: Authors credited in documentation

## 📞 Getting Help

### Resources

- **[Documentation Index](DOCUMENTATION.md)**: Complete documentation guide
- **[API Documentation](server/README.md)**: Detailed API reference
- **[Docker Guide](docker/README.md)**: Deployment and operations
- **[Troubleshooting](README.md#troubleshooting)**: Common issues and solutions

### Support Channels

1. **GitHub Issues**: For bugs and feature requests
2. **GitHub Discussions**: For questions and community support
3. **Documentation**: For comprehensive guides and references

### Response Times

- **Bug reports**: 1-3 business days
- **Feature requests**: 1-7 business days
- **Pull requests**: 1-5 business days
- **Questions**: 1-3 business days

## 📈 Project Roadmap

### Current Focus (v1.x)

- ✅ Core MCP server functionality
- ✅ Docker deployment
- ✅ Comprehensive documentation
- 🔄 CI/CD pipeline improvements
- 🔄 Performance optimizations

### Near Term (v2.x)

- 📋 IDE plugin development
- 📋 Authentication and authorization
- 📋 Advanced vector search features
- 📋 Monitoring and observability

### Long Term (v3.x+)

- 📋 Multi-tenant support
- 📋 Cloud deployment options
- 📋 Advanced analytics
- 📋 Plugin ecosystem

## 🎉 Thank You!

Thank you for contributing to GraphMemory-IDE! Your contributions help make this project better for everyone.

---

**Questions?** Feel free to open an issue or start a discussion. We're here to help! 🚀 