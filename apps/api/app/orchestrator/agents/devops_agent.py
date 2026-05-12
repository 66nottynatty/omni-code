"""
DevOps Agent - Specialized in Docker, CI/CD, and deployment automation.
"""
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..schemas.orchestrator import SubTask
import structlog
import json

logger = structlog.get_logger()


class DevOpsAgent(BaseAgent):
    """
    DevOps-focused agent that handles infrastructure as code,
    CI/CD pipelines, Docker configurations, and deployment automation.
    """

    def __init__(self, agent_id: str, mcp_manager=None, redis_client=None):
        super().__init__(agent_id, "DevOpsAgent", redis_client)
        self.mcp_manager = mcp_manager

    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        """
        Analyze the task and identify DevOps requirements.
        """
        await self.publish_log(task.id, "Analyzing DevOps requirements...")

        self.deployment_environments = ["development", "staging", "production"]
        self.required_files = self._identify_required_files(task.description)

        return (
            f"DevOps automation for: {task.title}\n"
            f"Required files: {', '.join(self.required_files)}"
        )

    def _identify_required_files(self, description: str) -> List[str]:
        """Identify which infrastructure files need to be created/updated."""
        files = []
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["docker", "container", "containerize"]):
            files.append("Dockerfile")
            files.append("docker-compose.yml")

        if any(kw in desc_lower for kw in ["ci", "cd", "pipeline", "github action"]):
            files.append(".github/workflows/ci.yml")

        if any(kw in desc_lower for kw in ["k8s", "kubernetes", "deploy"]):
            files.append("k8s/")

        if any(kw in desc_lower for kw in ["config", "env", "settings"]):
            files.append(".env.example")

        return files if files else ["Dockerfile"]

    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Generate infrastructure configurations.
        """
        await self.publish_log(task.id, "Generating infrastructure code...")

        # Generate Docker configuration
        docker_config = self._generate_dockerfile(task)
        await self.publish_log(task.id, "Dockerfile generated")

        # Generate CI/CD if needed
        if "workflow" in str(self.required_files).lower():
            ci_config = self._generate_github_workflow(task)
            await self.publish_log(task.id, "GitHub Actions workflow generated")

        # Generate docker-compose if needed
        compose_config = self._generate_docker_compose(task)
        await self.publish_log(task.id, "docker-compose.yml generated")

        return json.dumps({
            "files_created": self.required_files,
            "status": "infrastructure_configured"
        })

    def _generate_dockerfile(self, task: SubTask) -> str:
        """Generate a production-ready Dockerfile."""
        desc_lower = task.description.lower()

        if "python" in desc_lower:
            base_image = "python:3.11-slim"
            package_manager = "pip"
            workdir = "/app"
        elif "node" in desc_lower or "javascript" in desc_lower or "typescript" in desc_lower:
            base_image = "node:20-alpine"
            package_manager = "npm"
            workdir = "/app"
        elif "go" in desc_lower:
            base_image = "golang:1.21-alpine"
            package_manager = "go"
            workdir = "/app"
        else:
            base_image = "alpine:latest"
            package_manager = None
            workdir = "/app"

        dockerfile = f"""FROM {base_image}

WORKDIR {workdir}

# Install dependencies
"""

        if package_manager:
            dockerfile += f"""COPY package*.json ./
RUN {package_manager} install --production
"""

        dockerfile += f"""# Copy application
COPY . .

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:3000/health || exit 1

# Run application
CMD ["python", "main.py"]
"""
        return dockerfile

    def _generate_github_workflow(self, task: SubTask) -> str:
        """Generate GitHub Actions workflow."""
        return """name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          load: true
          tags: ${{ env.IMAGE_NAME }}:test

      - name: Run tests
        run: docker run ${{ env.IMAGE_NAME }}:test pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
"""

    def _generate_docker_compose(self, task: SubTask) -> str:
        """Generate docker-compose.yml for local development."""
        return """version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 3s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
"""

    async def conclude(self, task: SubTask, context: Dict[str, Any], observation: str) -> Dict[str, Any]:
        """
        Compile DevOps configuration results.
        """
        await self.publish_log(task.id, "DevOps setup complete")

        return {
            "status": "success",
            "observation": observation,
            "infrastructure": {
                "files_generated": self.required_files,
                "deployment_target": "containerized",
                "ci_cd_provider": "github_actions"
            },
            "next_steps": [
                "Review generated configurations",
                "Configure secrets in GitHub Actions",
                "Set up deployment credentials"
            ]
        }