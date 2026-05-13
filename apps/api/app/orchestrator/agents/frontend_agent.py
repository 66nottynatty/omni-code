"""
Frontend Agent - Specialized in React/Next.js components, CSS/UI refinement.
"""
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..schemas.orchestrator import SubTask
from app.intelligence.tools import read_file, write_file, read_skill
import structlog
import re


logger = structlog.get_logger()


class FrontendAgent(BaseAgent):
    """
    Frontend-focused agent that handles UI components,
    React/Next.js development, styling, and user experience optimization.
    """

    def __init__(self, agent_id: str, mcp_manager=None, redis_client=None):
        super().__init__(agent_id, "FrontendAgent", redis_client)
        self.mcp_manager = mcp_manager
        self.framework = None

    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        """
        Analyze the task and plan frontend implementation.
        """
        await self.publish_log(task.id, "Analyzing frontend requirements...")

        # Detect frontend framework
        self.framework = self._detect_framework(task.description)
        await self.publish_log(task.id, f"Detected framework: {self.framework}")

        # Load relevant skills
        skill_name = self._get_relevant_skill()
        if skill_name:
            skill_content = read_skill(skill_name)
            await self.publish_log(task.id, f"Loaded skill: {skill_name}")

        # Determine component structure
        component_type = self._determine_component_type(task)
        await self.publish_log(task.id, f"Component type: {component_type}")

        repo_map_info = f"## Repository Structure\n{context.get('repo_map', '')}\n\n"
        return repo_map_info + (
            f"Frontend implementation for: {task.title}\n"
            f"Framework: {self.framework}\n"
            f"Component: {component_type}\n"
            f"Description: {task.description}"
        )

    def _detect_framework(self, description: str) -> Dict[str, str]:
        """Detect the frontend framework from task description."""
        desc_lower = description.lower()
        framework = {
            "name": "react",
            "styling": "css",
            "state_management": "hooks",
            "component_type": "functional"
        }

        if "next" in desc_lower or "nextjs" in desc_lower or "next.js" in desc_lower:
            framework["name"] = "next.js"
            framework["meta"] = "app_router"
        elif "vue" in desc_lower:
            framework["name"] = "vue"
        elif "angular" in desc_lower:
            framework["name"] = "angular"

        if "tailwind" in desc_lower:
            framework["styling"] = "tailwind"
        elif "styled" in desc_lower or "css-in-js" in desc_lower:
            framework["styling"] = "styled-components"

        if "redux" in desc_lower:
            framework["state_management"] = "redux"
        elif "zustand" in desc_lower:
            framework["state_management"] = "zustand"

        return framework

    def _get_relevant_skill(self) -> Optional[str]:
        """Get the most relevant skill for the frontend task."""
        skill_mapping = {
            "react": "react_specialist",
            "next.js": "react_specialist",
            "vue": "vue_expert",
            "angular": "angular_expert"
        }
        return skill_mapping.get(self.framework.get("name"))

    def _determine_component_type(self, task: SubTask) -> str:
        """Determine what type of component to create."""
        desc_lower = task.description.lower()

        if any(kw in desc_lower for kw in ["button", "input", "form", "card"]):
            return "ui_component"
        elif any(kw in desc_lower for kw in ["page", "route", "layout"]):
            return "page"
        elif any(kw in desc_lower for kw in ["table", "list", "grid"]):
            return "data_display"
        elif any(kw in desc_lower for kw in ["modal", "dialog", "popup"]):
            return "overlay"
        else:
            return "generic_component"

    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Execute frontend implementation using tools.
        """
        await self.publish_log(task.id, "Generating frontend code...")

        file_path = task.input_data.get("file_path", "src/components/Component.tsx")

        # Generate component based on framework
        implementation = self._generate_component(task)

        # Write the implementation
        await self.publish_log(task.id, f"Writing to {file_path}")
        result = write_file(
            thread_id=task.input_data.get("thread_id", 0),
            file_path=file_path,
            content=implementation
        )

        # Generate associated styles if needed
        if self.framework.get("styling") == "css" and not file_path.endswith(".module.css"):
            style_path = file_path.replace(".tsx", ".module.css")
            styles = self._generate_css_module(task)
            write_file(
                thread_id=task.input_data.get("thread_id", 0),
                file_path=style_path,
                content=styles
            )
            await self.publish_log(task.id, f"Generated styles: {style_path}")

        return result

    def _generate_component(self, task: SubTask) -> str:
        """Generate component code based on framework."""
        framework_name = self.framework.get("name", "react")
        component_type = self._determine_component_type(task)

        if framework_name in ["react", "next.js"]:
            return self._generate_react_component(task)
        elif framework_name == "vue":
            return self._generate_vue_component(task)
        else:
            return self._generate_html_component(task)

    def _generate_react_component(self, task: SubTask) -> str:
        """Generate React/Next.js component."""
        component_type = self._determine_component_type(task)
        component_name = self._to_pascal_case(task.id.replace("-", "_"))
        prop_interface = f"{component_name}Props"

        base_component = f'''import React, {{ useState, useCallback }} from 'react';
import styles from './{component_name}.module.css';

interface {prop_interface} {{
  className?: string;
  onAction?: (data: unknown) => void;
}}

/**
 * {task.title}
 * 
 * {task.description}
 */
export const {component_name}: React.FC<{prop_interface}> = ({{
  className = '',
  onAction
}}) => {{
  const [isLoading, setIsLoading] = useState(false);
  const [data, setData] = useState<unknown>(null);

  const handleAction = useCallback(async () => {{
    setIsLoading(true);
    try {{
      // TODO: Implement action logic
      const result = await performAction();
      setData(result);
      onAction?.(result);
    }} catch (error) {{
      console.error('Action failed:', error);
    }} finally {{
      setIsLoading(false);
    }}
  }}, [onAction]);

  return (
    <div className={{`${{styles.container}} ${{className}}`}}>
      <h2 className={{styles.title}}>{task.title}</h2>
      <p className={{styles.description}}>{task.description}</p>
      
      <button
        className={{styles.button}}
        onClick={{handleAction}}
        disabled={{isLoading}}
      >
        {{isLoading ? 'Loading...' : 'Perform Action'}}
      </button>

      {{data && (
        <div className={{styles.result}}>
          <pre>{{JSON.stringify(data, null, 2)}}</pre>
        </div>
      )}}
    </div>
  );
}};

async function performAction(): Promise<unknown> {{
  // Placeholder for actual implementation
  return {{ success: true, timestamp: new Date().toISOString() }};
}}

export default {component_name};
'''

        if component_type == "form":
            return self._generate_form_component(task, component_name, prop_interface)
        elif component_type == "data_display":
            return self._generate_data_display_component(task, component_name, prop_interface)

        return base_component

    def _generate_form_component(self, task: SubTask, component_name: str, prop_interface: str) -> str:
        """Generate a form component."""
        return f'''"use client";

import React, {{ useState, FormEvent }} from 'react';
import styles from './{component_name}.module.css';

interface {prop_interface} {{
  onSubmit?: (formData: Record<string, string>) => void;
  initialData?: Record<string, string>;
}}

/**
 * {task.title} - Form Component
 */
export const {component_name}: React.FC<{prop_interface}> = ({{
  onSubmit,
  initialData = {{}}
}}) => {{
  const [formData, setFormData] = useState<Record<string, string>>(initialData);
  const [errors, setErrors] = useState<Record<string, string>>({{}});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {{
    const {{ name, value }} = e.target;
    setFormData(prev => ({{ ...prev, [name]: value }}));
    // Clear error on change
    if (errors[name]) {{
      setErrors(prev => {{...prev, [name]: ''}});
    }}
  }};

  const handleSubmit = async (e: FormEvent) => {{
    e.preventDefault();
    
    // Validate
    const newErrors: Record<string, string> = {{}};
    for (const [key, value] of Object.entries(formData)) {{
      if (!value.trim()) {{
        newErrors[key] = 'This field is required';
      }}
    }}
    
    if (Object.keys(newErrors).length > 0) {{
      setErrors(newErrors);
      return;
    }}

    onSubmit?.(formData);
  }};

  return (
    <form className={{styles.form}} onSubmit={{handleSubmit}}>
      <div className={{styles.field}}>
        <label htmlFor="input" className={{styles.label}}>Input Field</label>
        <input
          id="input"
          name="input"
          type="text"
          value={{formData.input || ''}}
          onChange={{handleChange}}
          className={{errors.input ? styles.inputError : styles.input}}
          placeholder="Enter value..."
        />
        {{errors.input && <span className={{styles.error}}>{{errors.input}}</span>}}
      </div>

      <button type="submit" className={{styles.submitButton}}>
        Submit
      </button>
    </form>
  );
}};

export default {component_name};
'''

    def _generate_data_display_component(self, task: SubTask, component_name: str, prop_interface: str) -> str:
        """Generate a data display component."""
        return f'''"use client";

import React, {{ useState, useEffect }} from 'react';
import styles from './{component_name}.module.css';

interface {prop_interface} {{
  dataUrl?: string;
  onRowClick?: (item: unknown) => void;
}}

interface DataItem {{
  id: string;
  name: string;
  status: string;
  updatedAt: string;
}}

/**
 * {task.title} - Data Display Component
 */
export const {component_name}: React.FC<{prop_interface}> = ({{
  dataUrl,
  onRowClick
}}) => {{
  const [items, setItems] = useState<DataItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState<keyof DataItem>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {{
    if (dataUrl) {{
      fetchData();
    }} else {{
      setLoading(false);
    }}
  }}, [dataUrl]);

  const fetchData = async () => {{
    try {{
      const response = await fetch(dataUrl);
      const result = await response.json();
      setItems(result);
    }} catch (error) {{
      console.error('Failed to fetch data:', error);
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleSort = (field: keyof DataItem) => {{
    if (field === sortField) {{
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    }} else {{
      setSortField(field);
      setSortDirection('asc');
    }}
  }};

  const sortedItems = [...items].sort((a, b) => {{
    const aVal = a[sortField];
    const bVal = b[sortField];
    const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortDirection === 'asc' ? comparison : -comparison;
  }});

  if (loading) {{
    return <div className={{styles.loading}}>Loading...</div>;
  }}

  return (
    <div className={{styles.container}}>
      <table className={{styles.table}}>
        <thead>
          <tr>
            <th onClick={{() => handleSort('name')}} className={{styles.sortableHeader}}>
              Name {{sortField === 'name' && (sortDirection === 'asc' ? '↑' : '↓')}}
            </th>
            <th onClick={{() => handleSort('status')}} className={{styles.sortableHeader}}>
              Status {{sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}}
            </th>
            <th onClick={{() => handleSort('updatedAt')}} className={{styles.sortableHeader}}>
              Updated {{sortField === 'updatedAt' && (sortDirection === 'asc' ? '↑' : '↓')}}
            </th>
          </tr>
        </thead>
        <tbody>
          {{sortedItems.map(item => (
            <tr
              key={{item.id}}
              onClick={{() => onRowClick?.(item)}}
              className={{styles.row}}
            >
              <td>{{item.name}}</td>
              <td><span className={{styles.badge}}>{{item.status}}</span></td>
              <td>{{new Date(item.updatedAt).toLocaleDateString()}}</td>
            </tr>
          ))}}
        </tbody>
      </table>
    </div>
  );
}};

export default {component_name};
'''

    def _generate_vue_component(self, task: SubTask) -> str:
        """Generate Vue component."""
        return f'''<template>
  <div class="{task.id}-container">
    <h2>{task.title}</h2>
    <p>{task.description}</p>
    <button @click="handleAction" :disabled="isLoading">
      {{ isLoading ? 'Loading...' : 'Perform Action' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import {{ ref }} from 'vue';

interface Props {{
  className?: string;
}}

const props = withDefaults(defineProps<Props>(), {{
  className: ''
}});

const emit = defineEmits<{{
  (e: 'action', data: unknown): void;
}}>();

const isLoading = ref(false);
const data = ref<unknown>(null);

const handleAction = async () => {{
  isLoading.value = true;
  try {{
    const result = await performAction();
    data.value = result;
    emit('action', result);
  }} catch (error) {{
    console.error('Action failed:', error);
  }} finally {{
    isLoading.value = false;
  }}
}};

const performAction = async (): Promise<unknown> => {{
  return {{ success: true, timestamp: new Date().toISOString() }};
}};
</script>

<style scoped>
.{task.id}-container {{
  padding: 1rem;
}}
</style>
'''

    def _generate_html_component(self, task: SubTask) -> str:
        """Generate basic HTML component."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{task.title}</title>
    <style>
        .container {{
            padding: 2rem;
            font-family: system-ui, sans-serif;
        }}
        .title {{
            font-size: 1.5rem;
            font-weight: bold;
        }}
        .description {{
            color: #666;
            margin: 1rem 0;
        }}
        .button {{
            padding: 0.5rem 1rem;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .button:hover {{
            background: #0056b3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">{task.title}</h1>
        <p class="description">{task.description}</p>
        <button class="button" onclick="handleAction()">Perform Action</button>
    </div>
    <script>
        async function handleAction() {{
            console.log('Action triggered');
            // TODO: Implement action logic
        }}
    </script>
</body>
</html>
'''

    def _generate_css_module(self, task: SubTask) -> str:
        """Generate CSS module for React components."""
        return f'''/* {task.title} styles */

.container {{
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}}

.title {{
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}}

.description {{
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 1rem;
}}

.button {{
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s;
}}

.button:hover:not(:disabled) {{
  background: #0056b3;
}}

.button:disabled {{
  opacity: 0.6;
  cursor: not-allowed;
}}

.result {{
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
}}

.result pre {{
  font-size: 0.75rem;
  overflow-x: auto;
}}

/* Form styles */
.form {{
  display: flex;
  flex-direction: column;
  gap: 1rem;
}}

.field {{
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}}

.label {{
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
}}

.input {{
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
}}

.inputError {{
  border-color: #dc3545;
}}

.error {{
  font-size: 0.75rem;
  color: #dc3545;
}}

.submitButton {{
  padding: 0.75rem;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}}

.submitButton:hover {{
  background: #218838;
}}
'''

    def _to_pascal_case(self, text: str) -> str:
        """Convert text to PascalCase."""
        words = re.sub(r'[^a-zA-Z0-9\s]', ' ', text).split()
        return ''.join(word.capitalize() for word in words)

    async def conclude(self, task: SubTask, context: Dict[str, Any], observation: str) -> Dict[str, Any]:
        """
        Compile frontend implementation results.
        """
        await self.publish_log(task.id, "Frontend implementation complete")

        return {
            "status": "success",
            "observation": observation,
            "implementation": {
                "framework": self.framework,
                "component_type": self._determine_component_type(task),
                "files_created": [
                    task.input_data.get("file_path", "src/components/Component.tsx")
                ]
            },
            "next_steps": [
                "Add component tests",
                "Integrate with parent components",
                "Test responsive design",
                "Verify accessibility"
            ]
        }