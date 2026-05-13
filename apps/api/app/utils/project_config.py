import json
import os
from typing import Dict, Any, Optional

def get_project_config(repo_path: str) -> Dict[str, Any]:
    """
    Read project configuration from the repository root.
    Looks for omnicode.json, then pyproject.toml, then package.json.
    """
    # 1. Try omnicode.json
    omnicode_json = os.path.join(repo_path, "omnicode.json")
    if os.path.exists(omnicode_json):
        try:
            with open(omnicode_json, "r") as f:
                return json.load(f)
        except:
            pass
            
    # 2. Try pyproject.toml
    pyproject_toml = os.path.join(repo_path, "pyproject.toml")
    if os.path.exists(pyproject_toml):
        try:
            import tomllib
            with open(pyproject_toml, "rb") as f:
                data = tomllib.load(f)
                return data.get("tool", {}).get("omnicode", {})
        except ImportError:
            try:
                import toml
                with open(pyproject_toml, "r") as f:
                    data = toml.load(f)
                    return data.get("tool", {}).get("omnicode", {})
            except:
                pass
        except:
            pass
            
    # 3. Try package.json
    package_json = os.path.join(repo_path, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, "r") as f:
                data = json.load(f)
                return data.get("omnicode", {})
        except:
            pass
            
    return {}
