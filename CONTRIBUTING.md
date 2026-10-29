# Contributing to Local Knowledge Graph

Thank you for contributing! We welcome contributions to make local-first knowledge management accessible, secure, and performant.

## Development Setup

1. Clone repository:
   ```bash
   git clone https://github.com/0xyz-exe/local-knowledge-graph.git
   cd local-knowledge-graph
   ```

2. Set up Python backend:
   ```bash
   uv venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   uv pip install -r requirements.txt
   ```

3. Set up Frontend:
   ```bash
   cd apps/web
   npm install
   ```

4. Run tests:
   ```bash
   python -m pytest backend/tests tests/test_e2e_playwright.py
   npm run build
   ```

## Pull Request Guidelines

- Ensure tests pass with 100% success.
- Maintain zero external cloud dependency requirements for core functionality.
- Write clear commit messages adhering to Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
