from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

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
    file_path: str = "Kleinanzeigen_Data/kleinanzeigen_items.json"

    def _run(self, request: str = "read") -> str:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found at {self.file_path}. The scraper might not have run yet."
        except Exception as e:
            return f"Error reading file: {str(e)}"