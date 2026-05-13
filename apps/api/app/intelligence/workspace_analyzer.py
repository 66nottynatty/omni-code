"""
Workspace Analyzer - Analyzes workspace structure and dependencies.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, List
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkspaceAnalyzer:
    """Analyzes a workspace to create a tailored profile skill."""

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.results: Dict = {}

    def analyze(self) -> Dict:
        """Run all analyses on the workspace."""
        self.results = {
            "tech_stack": self.detect_tech_stack(),
            "dependencies": self.analyze_dependencies(),
            "file_structure": self.analyze_file_structure(),
            "architecture": self.detect_architecture(),
            "config_files": self.find_config_files(),
            "omnicode_config": self._read_omnicode_config(),
        }
        return self.results

    def _read_omnicode_config(self) -> Dict:
        """Read .omnicode configuration file (JSON or YAML)."""
        config = {}
        
        # Try JSON
        if self._has_file('.omnicode'):
            try:
                config = self._read_json('.omnicode')
                if config:
                    return config
            except:
                pass
        
        # Try YAML
        if self._has_file('.omnicode.yaml') or self._has_file('.omnicode.yml'):
            try:
                import yaml
                path = self.workspace_path / '.omnicode.yaml'
                if not path.exists():
                    path = self.workspace_path / '.omnicode.yml'
                
                if path.exists():
                    with open(path) as f:
                        config = yaml.safe_load(f) or {}
                        if config:
                            return config
            except:
                pass
                
        return config

    def detect_tech_stack(self) -> Dict[str, List[str]]:
        """Detect the technology stack based on file patterns."""
        tech_stack = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": [],
        }

        # Detect languages by file extensions
        file_extensions = self._get_extensions()
        
        if any(ext in ['.py'] for ext in file_extensions):
            tech_stack["languages"].append("Python")
        if any(ext in ['.ts', '.tsx', '.js', '.jsx'] for ext in file_extensions):
            tech_stack["languages"].append("JavaScript/TypeScript")
        if any(ext in ['.java'] for ext in file_extensions):
            tech_stack["languages"].append("Java")
        if any(ext in ['.go'] for ext in file_extensions):
            tech_stack["languages"].append("Go")
        if any(ext in ['.rs'] for ext in file_extensions):
            tech_stack["languages"].append("Rust")
        if any(ext in ['.rb'] for ext in file_extensions):
            tech_stack["languages"].append("Ruby")
        if any(ext in ['.php'] for ext in file_extensions):
            tech_stack["languages"].append("PHP")
        if any(ext in ['.cs'] for ext in file_extensions):
            tech_stack["languages"].append("C#")

        # Detect frameworks
        if self._has_file('package.json'):
            tech_stack["frameworks"].append("Node.js")
            pkg = self._read_json('package.json')
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            if 'next' in deps:
                tech_stack["frameworks"].append("Next.js")
            if 'react' in deps:
                tech_stack["frameworks"].append("React")
            if 'vue' in deps:
                tech_stack["frameworks"].append("Vue.js")
            if 'angular' in deps:
                tech_stack["frameworks"].append("Angular")
            if 'express' in deps:
                tech_stack["frameworks"].append("Express")
            if 'fastapi' in str(deps) or 'flask' in str(deps):
                tech_stack["frameworks"].append("Python Web Framework")
        
        if self._has_file('requirements.txt'):
            reqs = self._read_requirements()
            if 'fastapi' in reqs:
                tech_stack["frameworks"].append("FastAPI")
            if 'flask' in reqs:
                tech_stack["frameworks"].append("Flask")
            if 'django' in reqs:
                tech_stack["frameworks"].append("Django")
            if 'sqlalchemy' in reqs:
                tech_stack["frameworks"].append("SQLAlchemy")

        if self._has_file('go.mod'):
            tech_stack["frameworks"].append("Go")
            if self._has_file('go.sum'):
                tech_stack["tools"].append("Go Modules")

        if self._has_file('Cargo.toml'):
            tech_stack["frameworks"].append("Rust")
            tech_stack["tools"].append("Cargo")

        # Detect databases
        if self._has_file('docker-compose.yml') or self._has_file('docker-compose.yaml'):
            compose = self._read_yaml()
            if compose:
                services = compose.get('services', {})
                for service in services:
                    if 'postgres' in service:
                        tech_stack["databases"].append("PostgreSQL")
                    if 'mysql' in service:
                        tech_stack["databases"].append("MySQL")
                    if 'mongo' in service:
                        tech_stack["databases"].append("MongoDB")
                    if 'redis' in service:
                        tech_stack["databases"].append("Redis")

        if self._has_file('*.env') or self._has_file('.env.example'):
            tech_stack["tools"].append("Environment Variables")

        return tech_stack

    def analyze_dependencies(self) -> Dict:
        """Analyze project dependencies."""
        dependencies = {
            "production": [],
            "development": [],
        }

        if self._has_file('package.json'):
            pkg = self._read_json('package.json')
            dependencies["production"] = list(pkg.get('dependencies', {}).keys())
            dependencies["development"] = list(pkg.get('devDependencies', {}).keys())

        if self._has_file('requirements.txt'):
            dependencies["production"] = self._read_requirements()

        if self._has_file('pyproject.toml'):
            try:
                toml_content = self._read_toml()
                if toml_content:
                    deps = toml_content.get('project', {}).get('dependencies', [])
                    dependencies["production"] = deps
            except:
                pass

        return dependencies

    def analyze_file_structure(self) -> List[str]:
        """Analyze the file structure."""
        structure = []
        
        if not self.workspace_path.exists():
            return structure

        try:
            for item in sorted(self.workspace_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    structure.append(f"{item.name}/")
                elif item.is_file() and not item.name.startswith('.'):
                    structure.append(item.name)
        except PermissionError:
            pass

        return structure[:50]  # Limit to top-level items

    def detect_architecture(self) -> Dict[str, str]:
        """Detect the architecture pattern."""
        architecture = {
            "pattern": "Unknown",
            "description": "",
        }

        # Check for common patterns
        has_api = self._has_file('app/api/') or self._has_file('routes/') or self._has_file('endpoints/')
        has_models = self._has_file('models/') or self._has_file('app/models/')
        has_services = self._has_file('services/') or self._has_file('app/services/')
        has_controllers = self._has_file('controllers/') or self._has_file('app/controllers/')

        if has_api and has_models and has_services:
            architecture["pattern"] = "Layered Architecture"
            architecture["description"] = "Uses API routes, services, and models separation"
        elif has_api and has_controllers:
            architecture["pattern"] = "MVC Pattern"
            architecture["description"] = "Uses API with controller pattern"
        elif self._has_file('app/') and self._has_file('src/'):
            architecture["pattern"] = "Modular Monolith"
            architecture["description"] = "Contains app and src directories"
        elif self._has_file('graphql/') or self._has_file('schema/'):
            architecture["pattern"] = "GraphQL API"
            architecture["description"] = "Uses GraphQL for API"

        # Check for microservices indicators
        if self._has_file('docker-compose.yml'):
            compose = self._read_yaml()
            if compose and len(compose.get('services', {})) > 3:
                architecture["pattern"] = "Microservices"
                architecture["description"] = "Multiple services in docker-compose"

        # Check for serverless indicators
        if self._has_file('serverless.yml') or self._has_file('.serverless/'):
            architecture["pattern"] = "Serverless"
            architecture["description"] = "Uses serverless framework"

        return architecture

    def find_config_files(self) -> List[str]:
        """Find configuration files."""
        config_patterns = [
            'package.json', 'package-lock.json', 'yarn.lock',
            'requirements.txt', 'Pipfile', 'Pipfile.lock', 'pyproject.toml',
            'go.mod', 'go.sum', 'Cargo.toml',
            'docker-compose.yml', 'docker-compose.yaml', 'Dockerfile',
            '.env.example', '.env.template',
            'tsconfig.json', '.eslintrc', '.prettierrc',
            'jest.config.js', 'vitest.config.ts', 'pytest.ini',
            'next.config.js', 'vite.config.ts',
            '.gitignore', '.dockerignore', '.omnicode', '.omnicode.yaml', '.omnicode.yml'
        ]
        
        configs = []
        for pattern in config_patterns:
            if self._has_file(pattern):
                configs.append(pattern)
        
        return configs

    def generate_profile_skill(self) -> str:
        """Generate a workspace profile skill as markdown."""
        self.analyze()
        
        tech = self.results.get("tech_stack", {})
        deps = self.results.get("dependencies", {})
        structure = self.results.get("file_structure", [])
        arch = self.results.get("architecture", {})
        configs = self.results.get("config_files", [])
        
        content = f"""# Workspace Profile

This is an auto-generated profile for this workspace, providing context about the technology stack and project structure.

## Technology Stack

### Languages
{', '.join(tech.get('languages', []) or ['Not detected'])}

### Frameworks
{', '.join(tech.get('frameworks', []) or ['Not detected'])}

### Databases
{', '.join(tech.get('databases', []) or ['Not detected'])}

### Tools
{', '.join(tech.get('tools', []) or ['Not detected'])}

## Architecture Pattern

**Pattern**: {arch.get('pattern', 'Unknown')}

{arch.get('description', '')}

## Key Dependencies

### Production Dependencies
"""
        
        prod_deps = deps.get("production", [])
        if prod_deps:
            content += "\n```\n" + "\n".join(prod_deps[:20]) + "\n```\n"
        else:
            content += "No production dependencies detected.\n"

        content += "\n### Development Dependencies\n"
        dev_deps = deps.get("development", [])
        if dev_deps:
            content += "\n```\n" + "\n".join(dev_deps[:15]) + "\n```\n"
        else:
            content += "No development dependencies detected.\n"

        content += "\n## Configuration Files\n"
        if configs:
            content += "\n".join([f"- {c}" for c in configs]) + "\n"
        else:
            content += "No standard config files detected.\n"

        content += "\n## Top-Level Structure\n"
        if structure:
            content += "\n```\n" + "\n".join(structure) + "\n```\n"
        else:
            content += "Unable to analyze structure.\n"

        content += """
## Important Notes

- This profile is auto-generated and may not capture all project details
- Always verify technology stack with actual code analysis
- Consult README or documentation for project-specific conventions

## Development Guidelines

When working in this workspace:

1. **Follow existing patterns**: Observe the code style and conventions already in use
2. **Update dependencies carefully**: Check for compatibility with existing dependencies
3. **Run existing tests**: Ensure any changes don't break existing functionality
4. **Check CI configuration**: Look at GitHub Actions or other CI configs for build/test commands
"""
        
        return content

    # Helper methods
    def _get_extensions(self) -> set:
        """Get all file extensions in workspace."""
        extensions = set()
        try:
            for root, dirs, files in os.walk(self.workspace_path):
                # Skip hidden and common ignore directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'target']]
                for file in files:
                    if '.' in file:
                        ext = '.' + file.rsplit('.', 1)[1]
                        extensions.add(ext)
        except PermissionError:
            pass
        return extensions

    def _has_file(self, path: str) -> bool:
        """Check if a file or directory exists."""
        check_path = self.workspace_path / path.replace('*', '')
        return check_path.exists()

    def _read_json(self, path: str) -> dict:
        """Read and parse a JSON file."""
        try:
            file_path = self.workspace_path / path
            if file_path.exists():
                with open(file_path) as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}

    def _read_requirements(self) -> List[str]:
        """Read requirements.txt."""
        try:
            req_path = self.workspace_path / 'requirements.txt'
            if req_path.exists():
                with open(req_path) as f:
                    return [
                        line.strip() for line in f
                        if line.strip() and not line.startswith('#')
                    ]
        except IOError:
            pass
        return []

    def _read_yaml(self) -> dict:
        """Read YAML file."""
        try:
            import yaml
            compose_path = self.workspace_path / 'docker-compose.yml'
            if not compose_path.exists():
                compose_path = self.workspace_path / 'docker-compose.yaml'
            
            if compose_path.exists():
                with open(compose_path) as f:
                    return yaml.safe_load(f) or {}
        except ImportError:
            pass
        except (yaml.YAMLError, IOError):
            pass
        return {}

    def _read_toml(self) -> dict:
        """Read TOML file."""
        try:
            import tomllib
            pyproject = self.workspace_path / 'pyproject.toml'
            if pyproject.exists():
                with open(pyproject, 'rb') as f:
                    return tomllib.load(f)
        except ImportError:
            try:
                import tomli
                pyproject = self.workspace_path / 'pyproject.toml'
                if pyproject.exists():
                    with open(pyproject, 'rb') as f:
                        return tomli.load(f)
            except ImportError:
                pass
            except Exception:
                pass
        except Exception:
            pass
        return {}


def analyze_workspace(workspace_path: str) -> Dict:
    """Analyze a workspace and return results."""
    analyzer = WorkspaceAnalyzer(workspace_path)
    return analyzer.analyze()


def generate_workspace_skill(workspace_path: str, workspace_id: int) -> tuple[str, Dict]:
    """
    Analyze a workspace and generate a profile skill.
    
    Returns:
        Tuple of (skill_content, analysis_results)
    """
    analyzer = WorkspaceAnalyzer(workspace_path)
    results = analyzer.analyze()
    content = analyzer.generate_profile_skill()
    return content, results
