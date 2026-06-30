# Contributing to Agent Orchestration System

Thank you for your interest in contributing to the **Agent Orchestration System**! We welcome contributions from developers, researchers, and AI engineers.

To maintain high code quality and smooth collaboration, please follow these guidelines.

## Code of Conduct
By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

1. **Fork and Clone** the repository:
   ```bash
   git clone https://github.com/divyyadav007/Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop.git
   cd Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop
   ```

2. **Create a Virtual Environment** and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```

4. **Run Services**:
   Ensure Redis is running locally or via Docker:
   ```bash
   docker-compose up -d redis
   ```

## Development Workflow

We use a standard Git branch workflow:
1. Create a branch from `main` or `master`: `git checkout -b feature/your-feature-name` or `bugfix/your-bugfix-name`.
2. Write clean, readable code with type hints, logging, and docstrings.
3. Verify your changes pass local linting and tests:
   ```bash
   black --check src tests
   flake8 src tests
   pytest tests/
   ```

## Conventional Commits
We follow the **Conventional Commits** specification for commit messages:
* `feat:` A new feature or specialized agent
* `fix:` A bug fix in routing, verification, or UI
* `docs:` Documentation improvements
* `style:` Formatting, missing semi-colons, etc (no production code change)
* `refactor:` Refactoring code structure (no behavior change)
* `test:` Adding or cleaning up tests
* `chore:` Updating build tasks, dependencies, etc.

Example:
```bash
feat: add data analysis node and selector mapping
fix: resolve redis connection fallback issue
docs: update human loop architecture diagram
```

## Submitting Pull Requests
- Keep your PRs focused and small.
- Fill out the provided Pull Request template.
- Ensure that the GitHub Actions CI pipelines pass before requesting review.
