# Contributing to OmniHub

Thank you for your interest in contributing to **OmniHub**! We welcome bug reports, feature suggestions, documentation improvements, and code pull requests.

## How Can I Contribute?

### 1. Reporting Bugs
- Search existing issues to ensure the bug hasn't already been reported.
- Open a new issue with a clear title and description.
- Include OS version, Python version, steps to reproduce, and terminal output or logs from `~/.config/omnihub/logs/`.

### 2. Suggesting Features
- Open an issue describing your proposed feature, use case, and suggested workflow.

### 3. Pull Requests
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/OmniHub.git
   cd OmniHub
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/amazing-idea
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Make your improvements while maintaining clean code formatting.
6. Verify your changes pass all automated test suites:
   ```bash
   python3 verify.py
   python3 selftest.py
   ```
7. Commit and push:
   ```bash
   git commit -m "feat: add amazing new feature"
   git push origin feature/amazing-idea
   ```
8. Open a Pull Request on the main repository.

---

## Community & Conduct

Please be respectful and constructive in all community interactions.

Engineered with ❤️ by **Md Sojib Hossain (SojibLabs)**.
