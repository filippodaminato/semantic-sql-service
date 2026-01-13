# Contributing Guide

Thank you for your interest in contributing to the Semantic SQL Engine! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Pull Request Process](#pull-request-process)
- [Code Review Guidelines](#code-review-guidelines)
- [Commit Message Format](#commit-message-format)

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/semantic-sql-service.git
   cd semantic-sql-service
   ```

3. **Set up development environment**
   - Follow the [Developer Guide](DEVELOPER_GUIDE.md#setup)
   - Ensure all tests pass: `docker-compose exec api pytest`

4. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

## Development Process

### Before You Start

1. **Check existing issues** - Your idea might already be discussed
2. **Create an issue** - For significant changes, discuss first
3. **Get feedback** - Wait for maintainer feedback before starting

### Making Changes

1. **Follow code style** - See [CODE_STYLE.md](CODE_STYLE.md)
2. **Write tests** - All new code should have tests
3. **Update documentation** - Update relevant docs
4. **Keep commits focused** - One logical change per commit

### Testing

- **Run tests locally** before submitting PR
- **Ensure all tests pass**: `docker-compose exec api pytest`
- **Check coverage**: Aim for >80% coverage on new code
- **Test edge cases**: Include error scenarios

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages follow format (see below)
- [ ] No merge conflicts with main branch

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated checks** - CI runs tests and linting
2. **Code review** - At least one maintainer reviews
3. **Address feedback** - Make requested changes
4. **Approval** - Once approved, PR is merged

## Code Review Guidelines

### For Authors

- **Be open to feedback** - Reviews are collaborative
- **Respond to comments** - Acknowledge and address feedback
- **Keep PRs focused** - Smaller PRs are easier to review
- **Update PR description** - Keep it current with changes

### For Reviewers

- **Be constructive** - Focus on code, not person
- **Explain reasoning** - Help authors understand why
- **Be timely** - Respond within 2-3 business days
- **Approve when ready** - Don't block on minor issues

### Review Checklist

- [ ] Code follows style guide
- [ ] Logic is correct and efficient
- [ ] Error handling is appropriate
- [ ] Tests are comprehensive
- [ ] Documentation is updated
- [ ] No security issues
- [ ] Performance considerations addressed

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(ontology): add deep create endpoint for tables

Implements POST /api/v1/ontology/tables endpoint that allows
creating a table and all its columns in a single transaction.

Closes #123
```

```
fix(embedding): handle empty text in embedding generation

Returns zero vector for empty text instead of calling API.
Prevents unnecessary API calls and errors.

Fixes #456
```

```
docs(api): update API documentation with examples

Adds comprehensive examples for all endpoints including
request/response formats and error cases.
```

### Scope

Use the module or component name:
- `ontology`: Physical ontology endpoints
- `semantics`: Business semantics
- `embedding`: Embedding service
- `database`: Database models
- `docs`: Documentation

### Subject

- Use imperative mood: "add" not "added" or "adds"
- First letter lowercase
- No period at end
- Maximum 50 characters

### Body (Optional)

- Explain **what** and **why**, not **how**
- Wrap at 72 characters
- Can include multiple paragraphs

### Footer (Optional)

- Reference issues: `Closes #123`, `Fixes #456`
- Breaking changes: `BREAKING CHANGE: description`

## Areas for Contribution

### Code

- Bug fixes
- New features
- Performance improvements
- Code refactoring
- Test coverage

### Documentation

- API documentation
- Architecture documentation
- Code examples
- Tutorials
- Developer guides

### Testing

- Unit tests
- Integration tests
- Test coverage improvements
- Test utilities

## Questions?

- Open an issue for questions
- Check existing documentation
- Ask in discussions (if enabled)

Thank you for contributing! 🎉
