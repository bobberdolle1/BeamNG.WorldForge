# Contributing to BeamNG.WorldForge

First off, thank you for considering contributing to BeamNG.WorldForge! 🎉

It's people like you that make BeamNG.WorldForge such a great tool.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guides](#style-guides)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

---

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

**Be respectful, be constructive, be collaborative.**

---

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:
- Node.js 18+ and npm/pnpm
- Python 3.11+
- Docker & docker-compose (optional)
- Google Earth Engine account
- Ollama installed (for AI features)

### First Steps

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/your-username/BeamNG.WorldForge.git
   cd BeamNG.WorldForge
   ```

3. **Set up development environment:**
   See [docs/SETUP.md](docs/SETUP.md) for detailed instructions.

4. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 🤝 How Can I Contribute?

### Reporting Bugs 🐛

Before creating bug reports, please check existing issues to avoid duplicates.

**When you create a bug report, include:**
- Clear, descriptive title
- Detailed steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Environment details (OS, browser, versions)
- Error messages/logs

**Use this template:**
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g., Windows 11]
 - Browser: [e.g., Chrome 120]
 - Version: [e.g., v1.0.0]

**Additional context**
Any other relevant information.
```

### Suggesting Enhancements 💡

Enhancement suggestions are tracked as GitHub issues.

**When suggesting an enhancement, include:**
- Clear, descriptive title
- Detailed description of the proposed feature
- Why this enhancement would be useful
- Possible implementation approach (if you have ideas)
- Mockups or examples (if applicable)

### Contributing Code 💻

**Great areas to contribute:**

1. **New Features:**
   - Water bodies 3D rendering
   - Vegetation system
   - Weather effects
   - Additional AI models

2. **Improvements:**
   - Performance optimization
   - UI/UX enhancements
   - Accessibility improvements
   - Mobile responsiveness

3. **Bug Fixes:**
   - Check GitHub Issues for bugs
   - Fix and submit PR

4. **Documentation:**
   - Improve existing docs
   - Add tutorials
   - Translate docs
   - Add code examples

5. **Tests:**
   - Write unit tests
   - Add integration tests
   - Improve test coverage

---

## 🛠️ Development Setup

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Setup Google Earth Engine
# Place your gee-key.json in backend/config/

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### With Docker

```bash
docker-compose up
```

---

## 📐 Style Guides

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(3d): add water rendering
fix(api): handle empty road data
docs: update SETUP.md with Ollama instructions
refactor(terrain): optimize heightmap loading
```

### TypeScript/JavaScript Style

- Use TypeScript for new code
- Follow ESLint configuration
- Use functional components with hooks
- Props with TypeScript interfaces
- Meaningful variable names

**Example:**
```typescript
interface MapSelectorProps {
  selectedBBox: BoundingBox | null;
  onBBoxChange: (bbox: BoundingBox) => void;
}

export const MapSelector: React.FC<MapSelectorProps> = ({
  selectedBBox,
  onBBoxChange,
}) => {
  // Component logic
};
```

### Python Style

- Follow PEP 8
- Use type hints
- Docstrings for functions/classes
- Async/await for I/O operations

**Example:**
```python
async def generate_heightmap(
    dem_data: np.ndarray,
    output_path: Path,
    resolution: int = 1024
) -> Path:
    """
    Generate heightmap PNG from DEM data.
    
    Args:
        dem_data: Digital elevation model data
        output_path: Output file path
        resolution: Heightmap resolution
    
    Returns:
        Path to generated heightmap
    """
    # Function logic
```

### Documentation Style

- Use Markdown
- Clear headings hierarchy
- Code examples with syntax highlighting
- Screenshots/GIFs for visual features
- Links to related docs

---

## 🔄 Pull Request Process

### Before Submitting

1. **Test your changes:**
   ```bash
   # Run linters
   npm run lint
   python -m pylint backend/

   # Run tests
   npm test
   pytest
   ```

2. **Update documentation:**
   - Update README if needed
   - Add/update inline comments
   - Update relevant docs/

3. **Ensure clean commit history:**
   ```bash
   # Rebase if needed
   git rebase -i main

   # Squash commits if necessary
   ```

### Submitting

1. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open Pull Request** on GitHub

3. **Fill out PR template:**
   - Clear title
   - Description of changes
   - Related issues
   - Screenshots (if UI changes)
   - Checklist completed

4. **Address review comments:**
   - Be responsive to feedback
   - Make requested changes
   - Re-request review when done

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #(issue_number)

## Screenshots
If applicable.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests passing
```

---

## 🧪 Testing Guidelines

### Writing Tests

**Frontend:**
```typescript
describe('MapSelector', () => {
  it('should update bbox on selection', () => {
    // Test logic
  });
});
```

**Backend:**
```python
def test_heightmap_generation():
    """Test heightmap generation from DEM data"""
    # Test logic
```

### Running Tests

```bash
# Frontend
npm test

# Backend
pytest

# With coverage
pytest --cov=backend
```

---

## 📦 Project Structure

```
BeamNG.WorldForge/
├── backend/          # Python FastAPI backend
│   ├── api/         # API routes
│   ├── services/    # Business logic (8 modules)
│   └── models/      # Data models
├── frontend/        # React TypeScript frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   └── services/    # API client
└── docs/            # Documentation
```

---

## 🎯 Areas Needing Help

Current priorities:
- 💧 Water rendering in 3D
- 🌳 Vegetation system
- 📱 Mobile responsiveness
- 🧪 Test coverage
- 🌍 Internationalization
- ♿ Accessibility improvements

See [GitHub Issues](https://github.com/your-username/BeamNG.WorldForge/issues) for specific tasks.

---

## 💬 Communication

- **GitHub Issues:** Bug reports, feature requests
- **GitHub Discussions:** Questions, ideas
- **Pull Requests:** Code contributions

---

## 🙏 Recognition

Contributors will be:
- Listed in README.md
- Credited in release notes
- Thanked publicly (if desired)

---

## 📚 Resources

- [Project Documentation](docs/)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [Setup Guide](docs/SETUP.md)

---

## ❓ Questions?

Don't hesitate to ask questions!

- Open a [Discussion](https://github.com/your-username/BeamNG.WorldForge/discussions)
- Comment on relevant issues
- Reach out to maintainers

---

**Thank you for contributing to BeamNG.WorldForge!** 🎉

Together we're building something amazing! 🚀

---

*Last updated: 2025-10-21*

