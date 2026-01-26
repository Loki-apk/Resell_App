import json
import os
from pathlib import Path
from datetime import datetime
from resell_app.price_calculation import PriceCalculator

class ResellWorkflow:
    def __init__(self, app):
        self.app = app
        self.market_search = getattr(app, 'market_search', None)
        self.calc = PriceCalculator()
        self.out_dir = Path(f"./Output_Folder/research_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.out_dir.mkdir(parents=True, exist_ok=True)
        # Use absolute path for consistency with file_read_tool
        self.scraper_file = Path(__file__).parent.parent / "Kleinanzeigen_Data" / "kleinanzeigen_items.json"

    def _save(self, filename, data):
        with open(self.out_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _parse(self, raw):
        try: return json.loads(str(raw).strip().replace("```json", "").replace("```", ""))
        except: return str(raw).strip()

    def run(self, inputs):
        print(f"{'='*60}\nSTARTING PRODUCT PRICE ANALYSIS\n{'='*60}")
        
        # --- PHASE 1 ---
        res_p1 = self.app.analysis_and_query_crew().kickoff(inputs={**inputs, "iteration": 1, "image_analysis": "Context", "feedback": "None"})
        img_analysis = self._parse(res_p1.tasks_output[0].raw)
        self._save("image_analysis.json", img_analysis)
        
        # CHECK FOR IMAGE ANALYSIS ERRORS - STOP IF FOUND
        if isinstance(img_analysis, dict) and "error" in img_analysis:
            print(f"\n[!] Image Analysis Failed: {img_analysis.get('error')}")
            print(f"[!] Stopping workflow - inconsistent or invalid images")
            return {"success": False, "error": img_analysis.get("error"), "item_description": None, "best_iteration": 0, "best_result": {}, "history": []}
        
        history, best_res = [], {"match_percentage": 0}
        current_query_json = res_p1.tasks_output[1].raw
        feedback = "None"
        
        # Accumulator for valid matches
        all_unique_matches = {} 
        
        # --- PHASE 2: Loop ---
        for i in range(1, 4): 
            print(f"\n--- Iteration {i} ---")
            
            # 1. Query Gen
            if i > 1:
                res_gen = self.app.query_regeneration_crew().kickoff(inputs={**inputs, "iteration": i, "feedback": feedback, "image_analysis": json.dumps(img_analysis)})
                current_query_json = res_gen.raw

            query_data = self._parse(current_query_json)
            query = query_data.get("search_query", str(query_data)) if isinstance(query_data, dict) else str(query_data)
            print(f"Query: {query}")

            # 2. Run Fast Scraper
            if self.market_search:
                try: self.market_search.run(search_query=query, min_items=10)
                except Exception as e: print(f"Scraper Error: {e}")

            # 3. Check & Evaluate
            if not self.scraper_file.exists():
                print("No data found. Retrying.")
                continue

            eval_res = self.app.evaluation_crew().kickoff(inputs={**inputs, "image_analysis": json.dumps(img_analysis), "search_query": query, "scraped_data_file": "C:\\Sem_1_Project\\Resell App\\Kleinanzeigen_Input\\input_items.json", "feedback": feedback})
            
            # Parse Result (Agent now includes metrics via its tool)
            eval_data = self._parse(eval_res.raw)
            if not isinstance(eval_data, dict): eval_data = {"individual_results_evaluation": []}

            # 4. ACCUMULATE & CALCULATE PRICES
            current_matches = [item for item in eval_data.get("individual_results_evaluation", []) if item.get("is_match") or item.get("match_status")]
            for m in current_matches: all_unique_matches[str(m.get("id"))] = m
            
            # Calc stats on cumulative data
            stats = self.calc.calculate_from_evaluation({"individual_results_evaluation": list(all_unique_matches.values())})
            
            # Use metrics returned by Agent/Tool - prefer agent output if available
            count_positive = eval_data.get("count_positive")
            count_negative = eval_data.get("count_negative")
            total_listings = eval_data.get("total_listings")
            match_pct = eval_data.get("match_percentage", 0)
            
            # If agent didn't provide metrics, calculate them
            if count_positive is None:
                count_positive = len([e for e in eval_data.get("individual_results_evaluation", []) if e.get("is_match")])
            if count_negative is None:
                count_negative = len([e for e in eval_data.get("individual_results_evaluation", []) if not e.get("is_match")])
            if total_listings is None:
                total_listings = count_positive + count_negative
            
            print(f"Match: {match_pct}% | Positive: {count_positive} | Negative: {count_negative} | Total: {total_listings}")

            # 5. Save Step Result & Prepare for Next Iteration
            
            step_res = {
                "iteration": i, 
                "query": query, 
                "evaluation": eval_data, 
                "count_positive": count_positive,
                "count_negative": count_negative,
                "total_listings": total_listings,
                "match_percentage": match_pct, 
                "price_statistics": stats,
            }
            self._save(f"evaluation_{i}.json", step_res)
            history.append(step_res)

            if match_pct > best_res.get("match_percentage", -1): best_res = step_res
            if eval_data.get("overall_sufficiency") == "sufficient": return self._finalize(True, i, best_res, history, img_analysis)
            
            feedback = eval_data.get("query_improvement_feedback", "None")

        return self._finalize(False, best_res.get("iteration", 0), best_res, history, img_analysis)

    def _finalize(self, success, iter, best, hist, img_analysis):
        final = {
            "success": success,
            "best_iteration": iter,
            "item_description": img_analysis.get("description") if isinstance(img_analysis, dict) else None,
            "best_result": best,
            "history": hist
        }
        self._save("final_result.json", final)
        return final