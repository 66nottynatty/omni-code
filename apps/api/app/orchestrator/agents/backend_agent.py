"""
Backend Agent - Specialized in Python/Node development, database schema design.
"""
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..schemas.orchestrator import SubTask
from app.intelligence.tools import read_file, write_file, run_terminal, read_skill, search_codebase
import structlog
import json

logger = structlog.get_logger()


class BackendAgent(BaseAgent):
    """
    Backend-focused agent that handles server-side logic,
    database operations, API design, and backend architecture.
    """

    def __init__(self, agent_id: str, mcp_manager=None, redis_client=None):
        super().__init__(agent_id, "BackendAgent", redis_client)
        self.mcp_manager = mcp_manager
        self.tech_stack = None

    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        """
        Analyze the task and plan backend implementation.
        """
        await self.publish_log(task.id, "Analyzing backend requirements...")

        # Determine tech stack from task description
        self.tech_stack = self._detect_tech_stack(task.description)
        await self.publish_log(task.id, f"Detected stack: {self.tech_stack}")

        # Read relevant skills for the backend task
        skill_name = self._get_relevant_skill()
        if skill_name:
            skill_content = read_skill(skill_name)
            await self.publish_log(task.id, f"Loaded skill: {skill_name}")

        return (
            f"Backend implementation for: {task.title}\n"
            f"Tech stack: {self.tech_stack}\n"
            f"Description: {task.description}"
        )

    def _detect_tech_stack(self, description: str) -> Dict[str, str]:
        """Detect the technology stack from task description."""
        desc_lower = description.lower()
        stack = {"language": "python", "framework": "fastapi", "database": "postgresql"}

        if "node" in desc_lower or "express" in desc_lower:
            stack["language"] = "javascript"
            stack["framework"] = "express"
        elif "django" in desc_lower:
            stack["framework"] = "django"
        elif "flask" in desc_lower:
            stack["framework"] = "flask"
        elif "go" in desc_lower:
            stack["language"] = "go"
            stack["framework"] = "gin"
        elif "rust" in desc_lower:
            stack["language"] = "rust"
            stack["framework"] = "axum"

        if "mysql" in desc_lower:
            stack["database"] = "mysql"
        elif "mongodb" in desc_lower or "mongo" in desc_lower:
            stack["database"] = "mongodb"
        elif "sqlite" in desc_lower:
            stack["database"] = "sqlite"

        return stack

    def _get_relevant_skill(self) -> Optional[str]:
        """Get the most relevant skill for the backend task."""
        skill_mapping = {
            "fastapi": "fastapi_best_practices",
            "django": "django_expert",
            "flask": "flask_developer",
            "express": "nodejs_backend",
        }
        return skill_mapping.get(self.tech_stack.get("framework"))

    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Execute backend implementation using tools.
        """
        await self.publish_log(task.id, "Implementing backend logic...")

        # Get workspace context
        workspace_id = context.get("workspace_id")
        file_path = task.input_data.get("file_path", "src/main.py")

        # Search for relevant code in the codebase
        if workspace_id:
            search_results = search_codebase(workspace_id, task.description)
            if search_results:
                await self.publish_log(
                    task.id,
                    f"Found {len(search_results)} relevant code snippets"
                )

        # Generate implementation based on tech stack
        implementation = self._generate_implementation(task)

        # Write the implementation
        await self.publish_log(task.id, f"Writing to {file_path}")
        result = write_file(
            thread_id=task.input_data.get("thread_id", 0),
            file_path=file_path,
            content=implementation
        )

        # Run tests if available
        await self._run_tests(task)

        return result

    def _generate_implementation(self, task: SubTask) -> str:
        """Generate code implementation based on the tech stack."""
        stack = self.tech_stack

        if stack["language"] == "python" and stack["framework"] == "fastapi":
            return self._generate_fastapi_code(task)
        elif stack["language"] == "javascript" and stack["framework"] == "express":
            return self._generate_express_code(task)
        elif stack["language"] == "go":
            return self._generate_go_code(task)
        else:
            return self._generate_generic_code(task)

    def _generate_fastapi_code(self, task: SubTask) -> str:
        """Generate FastAPI application code."""
        return f'''"""
{task.title}
Auto-generated backend implementation
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import asyncpg
import structlog

logger = structlog.get_logger()

app = FastAPI(title="{task.title}", version="1.0.0")


class RequestModel(BaseModel):
    """Request validation model."""
    data: str = Field(..., min_length=1, max_length=1000)
    priority: int = Field(default=0, ge=0, le=10)


class ResponseModel(BaseModel):
    """Response model."""
    status: str
    result: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy", "timestamp": datetime.utcnow().isoformat()}}


@app.post("/api/{task.id}", response_model=ResponseModel)
async def process_request(request: RequestModel):
    """
    Process incoming request.
    
    Description: {task.description}
    """
    try:
        # TODO: Implement business logic
        result = await process_business_logic(request.data)
        
        return ResponseModel(
            status="success",
            result=result
        )
    except Exception as e:
        logger.error("request_processing_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def process_business_logic(data: str) -> dict:
    """
    Business logic implementation.
    Replace with actual implementation.
    """
    return {{"processed": data, "length": len(data)}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    def _generate_express_code(self, task: SubTask) -> str:
        """Generate Express.js application code."""
        return f'''/**
 * {task.title}
 * Auto-generated backend implementation
 */

const express = require('express');
const app = express();

app.use(express.json());

// Health check
app.get('/health', (req, res) => {{
    res.json({{ status: 'healthy', timestamp: new Date().toISOString() }});
}});

// Main endpoint
app.post('/api/{task.id}', async (req, res) => {{
    try {{
        const {{ data }} = req.body;
        
        // TODO: Implement business logic
        const result = await processBusinessLogic(data);
        
        res.json({{
            status: 'success',
            result,
            timestamp: new Date().toISOString()
        }});
    }} catch (error) {{
        console.error('Request processing failed:', error);
        res.status(500).json({{ error: error.message }});
    }}
}});

async function processBusinessLogic(data) {{
    // Business logic implementation
    return {{ processed: data, length: data.length }};
}}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {{
    console.log(`Server running on port ${{PORT}}`);
}});
'''

    def _generate_go_code(self, task: SubTask) -> str:
        """Generate Go application code."""
        return f'''// {task.title}
// Auto-generated backend implementation

package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type Request struct {{
    Data string `json:"data"`
}}

type Response struct {{
    Status    string    `json:"status"`
    Result    any       `json:"result,omitempty"`
    Timestamp time.Time `json:"timestamp"`
}}

func healthHandler(w http.ResponseWriter, r *http.Request) {{
    json.NewEncoder(w).Encode(map[string]any{{
        "status":    "healthy",
        "timestamp": time.Now().Format(time.RFC3339),
    }})
}}

func apiHandler(w http.ResponseWriter, r *http.Request) {{
    var req Request
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {{
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }}

    result := processBusinessLogic(req.Data)
    json.NewEncoder(w).Encode(Response{{
        Status:    "success",
        Result:    result,
        Timestamp: time.Now(),
    }})
}}

func processBusinessLogic(data string) map[string]any {{
    return map[string]any{{
        "processed": data,
        "length":    len(data),
    }}
}}

func main() {{
    http.HandleFunc("/health", healthHandler)
    http.HandleFunc("/api/{task.id}", apiHandler)
    
    fmt.Println("Server starting on :8080")
    http.ListenAndServe(":8080", nil)
}}
'''

    def _generate_generic_code(self, task: SubTask) -> str:
        """Generate generic backend code."""
        return f'''# {task.title}
# Auto-generated backend implementation
# Description: {task.description}

# Implementation placeholder
# TODO: Add actual implementation

def main():
    print("Backend service for {task.title}")
    pass

if __name__ == "__main__":
    main()
'''

    async def _run_tests(self, task: SubTask):
        """Run tests for the implemented code."""
        test_commands = {
            "python": ["pytest", "-v"],
            "javascript": ["npm", "test"],
            "go": ["go", "test", "-v"]
        }

        cmd = test_commands.get(self.tech_stack.get("language", "python"))
        if cmd:
            await self.publish_log(task.id, f"Running tests: {' '.join(cmd)}")
            result = run_terminal(
                thread_id=task.input_data.get("thread_id", 0),
                command=" ".join(cmd)
            )
            await self.publish_log(task.id, f"Test results: {result}")

    async def conclude(self, task: SubTask, context: Dict[str, Any], observation: str) -> Dict[str, Any]:
        """
        Compile backend implementation results.
        """
        await self.publish_log(task.id, "Backend implementation complete")

        return {
            "status": "success",
            "observation": observation,
            "implementation": {
                "tech_stack": self.tech_stack,
                "files_modified": [task.input_data.get("file_path", "src/main.py")],
                "tests_run": True
            },
            "next_steps": [
                "Review generated code",
                "Add unit tests",
                "Configure database connections",
                "Deploy to staging environment"
            ]
        }