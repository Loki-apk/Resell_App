import os, json, random, re, pandas as pd
from datetime import datetime
from resell_app.random_data import FastMarketSearch
from resell_app.crew import ResellApp
from resell_app.workflow import ResellWorkflow

class BenchmarkEngine:
    def __init__(self, category: str = None):
        self.scraper = FastMarketSearch()
        self.cat_filter = category
        self.results_dir = "benchmark_results"
        self.input_file = os.path.join("Kleinanzeigen_Input", "input_items.json")
        os.makedirs(self.results_dir, exist_ok=True)

    def start(self):
        print("\n=== Resell Benchmark Started ===")
        
        # 1. Scrape & Load (only if data doesn't exist)
        try:
            if not os.path.exists(self.input_file):
                print("[*] Scraping data...")
                self.scraper._run()
            else:
                print("[*] Data already exists, skipping scrape...")
            
            with open(self.input_file, 'r', encoding='utf-8') as f:
                items = json.load(f)
        except Exception as e:
            return print(f"[!] Data Error: {e}")

        # 2. Sample (10 Random Items)
        if self.cat_filter: 
            items = [i for i in items if i.get('category') == self.cat_filter]
        
        sample = random.sample(items, min(len(items), 10))
        print(f"Selected {len(sample)} items for benchmarking.\n")

        # 3. Run Workflow
        results = []
        workflow = ResellWorkflow(ResellApp())

        for i, item in enumerate(sample, 1):
            actual = self._parse_price(item.get('price'))
            imgs = item.get('local_images', [])
            
            if not actual or not imgs:
                print(f"[{i}] Skipped (Invalid Data)")
                continue

            print(f"[{i}] Benchmarking: {item.get('title', '')[:30]}... ({actual}€)")
            
            try:
                # Run Workflow
                res = workflow.run({"image_urls": imgs})
                
                # CHECK FOR ERRORS - Skip if image analysis failed
                if not res.get("success", True) and "error" in res:
                    print(f"    -> Skipped: {res.get('error')}")
                    continue
                
                # Extract Prediction
                stats = res.get("best_result", {}).get("price_statistics", {})
                if isinstance(stats, dict) and "price_statistics" in stats: stats = stats["price_statistics"]
                pred = float(stats.get("average_price", stats.get("median", 0.0)))

                # Calc Metrics
                err_pct = abs(pred - actual) / actual * 100
                
                results.append({
                    "id": item.get('id'), "category": item.get('category'),
                    "actual": actual, "predicted": pred, 
                    "error_pct": err_pct, 
                    "success": err_pct < 15.0
                })
                print(f"    -> Pred: {pred}€ | Error: {err_pct:.1f}% {'(✓)' if err_pct < 15 else '(✗)'}")

            except Exception as e:
                print(f"    -> Error: {e}")

        self._generate_report(results)

    def _generate_report(self, data):
        if not data: return print("No results generated.")
        
        df = pd.DataFrame(data)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save Raw Data
        df.to_csv(f"{self.results_dir}/benchmark_{ts}.csv", index=False)

        # Calculate Aggregates using Pandas (Replaces 50+ lines of manual looping)
        summary = df.groupby('category').agg(
            items=('id', 'count'),
            success_rate=('success', 'mean'),
            avg_error=('error_pct', 'mean')
        ).sort_values('success_rate', ascending=False)
        
        # Print Report
        print(f"\n{'='*40}\nBENCHMARK REPORT ({ts})\n{'='*40}")
        print(f"Total Accuracy: {(df['success'].mean() * 100):.1f}% | Avg Error: {df['error_pct'].mean():.1f}%")
        print("-" * 40)
        print(summary.to_string(formatters={'success_rate': '{:.1%}'.format, 'avg_error': '{:.1f}%'.format}))
        print("="*40)

    def _parse_price(self, p):
        try: return float(re.sub(r'[^\d,.]', '', str(p)).replace('.', '').replace(',', '.'))
        except: return None