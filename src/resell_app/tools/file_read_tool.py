from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from pathlib import Path
import json

class UTF8FileReadInput(BaseModel):
    """Input for UTF8FileReadTool."""
    # DUMMY ARGUMENT to prevent 'Action Input is not a valid key' error
    request: str = Field(
        default="read", 
        description="Ignore this field, just pass 'read'."
    )

class UTF8FileReadTool(BaseTool):
    name: str = "Read Local Database"
    description: str = "Reads the local kleinanzeigen_items.json database file. Input 'read' to start."
    args_schema: Type[BaseModel] = UTF8FileReadInput
    
    def _run(self, request: str = "read") -> str:
        try:
            # Use absolute path to ensure consistency regardless of working directory
            # Path(__file__).parent = src/resell_app/tools
            # Path(__file__).parent.parent.parent = src
            # Path(__file__).parent.parent.parent.parent = root project folder
            file_path = Path(__file__).parent.parent.parent.parent / "Kleinanzeigen_Data" / "kleinanzeigen_items.json"
            
            if not file_path.exists():
                return "[]"  # Return empty array instead of error - the agent expects this
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data)
        except FileNotFoundError:
            return "[]"  # Return empty array for consistency
        except json.JSONDecodeError:
            return "[]"  # Return empty array if file is corrupted
        except Exception as e:
            return f"[]"  # Return empty array on any error for graceful handling