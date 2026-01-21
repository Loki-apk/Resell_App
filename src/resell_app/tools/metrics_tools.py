import json
from typing import List, Dict, Union, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class MetricsToolInput(BaseModel):
    # This is the input schema the Agent sees
    evaluations: Union[List[Dict], str] = Field(
        ..., 
        description="The list of 'individual_results_evaluation' items."
    )

class EvaluationMetricsTool(BaseTool):
    name: str = "Evaluation Metrics Calculator"
    description: str = (
        "Calculates metrics for search results. "
        "Input: List of evaluations. Output: JSON with counts and percentages."
    )
    # Bind the input schema here
    args_schema: Type[BaseModel] = MetricsToolInput

    def _run(self, evaluations: Union[List[Dict], str]) -> str:
        if isinstance(evaluations, str):
            try: items = json.loads(evaluations)
            except: return "Error: Input must be a valid JSON list."
        else:
            items = evaluations

        if not isinstance(items, list): items = []

        # Count logic
        pos = sum(1 for i in items if isinstance(i, dict) and (i.get("is_match") is True or i.get("match_status") is True))
        total = len(items)
        pct = round((pos / total * 100), 2) if total > 0 else 0.0

        result = {
            "count_positive": pos,
            "count_negative": total - pos,
            "match_percentage": pct,
            "total_listings": total,
            "overall_sufficiency": "sufficient" if pct >= 70 else "not sufficient"
        }
        
        return json.dumps(result)