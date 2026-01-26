import json
from typing import List, Dict, Union, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class MetricsToolInput(BaseModel):
    evaluations: Union[List[Dict], str] = Field(
        ..., 
        description="List of data items. Can be search results (for sufficiency check) OR price predictions (for benchmarking)."
    )

class EvaluationMetricsTool(BaseTool):
    name: str = "Evaluation Metrics Calculator"
    description: str = (
        "Versatile metrics calculator. "
        "1. If input has 'predicted_price', calculates Price Deviance and Accuracy. "
        "2. If input has 'is_match', calculates Search Sufficiency."
    )
    args_schema: Type[BaseModel] = MetricsToolInput

    def _run(self, evaluations: Union[List[Dict], str]) -> str:
        # 1. PARSE INPUT
        if isinstance(evaluations, str):
            try: 
                items = json.loads(evaluations)
            except: 
                return json.dumps({"error": "Input must be a valid JSON list."})
        else:
            items = evaluations

        if not isinstance(items, list) or not items:
            return json.dumps({"error": "Empty dataset provided."})

        # 2. DETECT MODE (Price Benchmark vs Search Quality)
        first_item = items[0]
        
        # Check for Price Benchmarking keys (from your benchmark.py logic)
        if "predicted_price" in first_item and "actual_price" in first_item:
            return self._calculate_price_benchmarks(items)
        
        # Default to Search Quality (Your existing logic)
        else:
            return self._calculate_search_metrics(items)

    def _calculate_search_metrics(self, items: List[Dict]) -> str:
        """Original logic: Counts positive/negative search results."""
        pos = sum(1 for i in items if isinstance(i, dict) and (i.get("is_match") is True or i.get("match_status") is True))
        total = len(items)
        pct = round((pos / total * 100), 2) if total > 0 else 0.0

        result = {
            "metric_type": "search_quality",
            "count_positive": pos,
            "count_negative": total - pos,
            "match_percentage": pct,
            "total_listings": total,
            "overall_sufficiency": "sufficient" if pct >= 70 else "not sufficient"
        }
        return json.dumps(result, indent=2)

    def _calculate_price_benchmarks(self, items: List[Dict]) -> str:
        """New logic: Calculates Price Deviance and Success Rate."""
        total_items = len(items)
        success_count = 0
        total_error_pct = 0.0
        total_dev_eur = 0.0

        for item in items:
            actual = float(item.get("actual_price", 0))
            predicted = float(item.get("predicted_price", 0))
            
            # Avoid division by zero
            if actual == 0: 
                continue

            # Deviance Logic
            deviance = predicted - actual
            abs_error_pct = abs(deviance / actual) * 100
            
            total_dev_eur += abs(deviance)
            total_error_pct += abs_error_pct

            # Success Threshold (e.g., prediction is within 15% of actual)
            if abs_error_pct <= 15.0:
                success_count += 1

        # Aggregates
        avg_error_pct = round(total_error_pct / total_items, 2) if total_items > 0 else 0.0
        avg_dev_eur = round(total_dev_eur / total_items, 2) if total_items > 0 else 0.0
        success_rate = round((success_count / total_items) * 100, 2) if total_items > 0 else 0.0

        result = {
            "metric_type": "price_benchmark",
            "total_items": total_items,
            "successful_predictions": success_count,
            "success_rate": success_rate,
            "avg_error_percentage": avg_error_pct,
            "avg_deviance_eur": avg_dev_eur,
            "performance_status": "High Accuracy" if success_rate >= 80 else "Needs Improvement"
        }
        return json.dumps(result, indent=2)