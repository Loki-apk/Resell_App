#!/usr/bin/env python
import sys
import warnings
import crewai.utilities.printer as printer

from resell_app.benchmark import BenchmarkEngine
from resell_app.crew import ResellApp

if hasattr(printer, "_COLOR_CODES") and "orange" not in printer._COLOR_CODES:
    printer._COLOR_CODES["orange"] = "\033[38;5;208m"

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the benchmark engine.
    
    Optional: Pass category name as argument
    Example: crewai run "Audio & HiFi"
    """
    try:
        # Get category from command line if provided
        category = sys.argv[1] if len(sys.argv) > 1 else None
        
        # Initialize and start the benchmark engine
        engine = BenchmarkEngine(category=category)
        engine.start()
        
    except KeyboardInterrupt:
        print("\n\n[!] Execution stopped by user.")
        sys.exit(0)
    except Exception as e:
        raise Exception(f"An error occurred while running the benchmark: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ResellApp().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "image_urls": ""
    }

    try:
        # if using external triggers, still route through full pipeline
        result = ResellApp().run_full_pipeline(inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")

if __name__ == "__main__":
    run()