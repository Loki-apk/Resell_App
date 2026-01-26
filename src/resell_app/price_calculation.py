import re
from statistics import median
from typing import Dict, Optional

class PriceCalculator:
    """Calculates price statistics directly from the evaluation JSON."""
    
    @staticmethod
    def clean_price(val) -> Optional[float]:
        s = str(val).upper().strip()
        if not s or any(k in s for k in ['N/A', 'NULL', 'SUCHE', 'TAUSCH']): return None
        
        # Strip non-numeric/non-separator characters
        s = re.sub(r'[^\d,.]', '', s)
        
        # Handle European (1.234,56) vs US (1,234.56) formatting
        if ',' in s:
            # If comma is after the last dot (1.200,00) OR is near the end (1234,50), treat as decimal
            if ('.' in s and s.rfind(',') > s.rfind('.')) or (len(s) - s.rfind(',') <= 3):
                s = s.replace('.', '').replace(',', '.')
            else: # Treat comma as thousands separator (1,234)
                s = s.replace(',', '')
                
        try:
            return float(s) if float(s) > 0 else None
        except ValueError:
            return None

    def calculate_from_evaluation(self, evaluation: Dict) -> Dict:
        items = evaluation.get("individual_results_evaluation", [])
        
        # Filter positive matches and clean prices
        prices = sorted([p for i in items if (i.get("is_match") or i.get("match_status")) and (p := self.clean_price(i.get("price"))) is not None])
        
        # Default stats
        stats = {
            "count": 0, 
            "median": 0,
            "average_price": 0,
            "range": "N/A", 
            "valid_prices": []
        }
        
        if prices:
            # Format helper: 70.0 -> 70, 70.5 -> 70.5
            fmt = lambda x: int(x) if x.is_integer() else x
            avg_price = sum(prices) / len(prices)
            
            stats.update({
                "count": len(prices),
                "median": round(median(prices), 2),
                "average_price": round(avg_price, 2),
                # Combine min and max into a single string
                "range": f"{fmt(prices[0])}-{fmt(prices[-1])}",
                "valid_prices": prices
            })
        
        return {
            "positive_match_count": len([i for i in items if i.get("is_match") or i.get("match_status")]), 
            "price_statistics": stats
        }