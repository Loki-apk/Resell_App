# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information
#!/usr/bin/env python
import sys
import warnings
import crewai.utilities.printer as printer

if hasattr(printer, "_COLOR_CODES") and "orange" not in printer._COLOR_CODES:
    printer._COLOR_CODES["orange"] = "\033[38;5;208m"

from datetime import datetime
from resell_app.crew import ResellApp

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    inputs = {
        "image_urls": [
            'https://img.kleinanzeigen.de/api/v1/prod-ads/images/ef/efa2fbca-87a0-4c82-8d7a-39129a68a7aa?rule=$_59.AUTO',
            'https://img.kleinanzeigen.de/api/v1/prod-ads/images/4a/4aba62c0-889a-4538-aaf4-b1b19126f857?rule=$_59.AUTO',
            'https://img.kleinanzeigen.de/api/v1/prod-ads/images/69/6901fe7d-01ab-471f-955c-3f1297f851c0?rule=$_59.AUTO',
            'https://img.kleinanzeigen.de/api/v1/prod-ads/images/45/45ed7992-98ed-49e5-882f-86abc3e55346?rule=$_59.AUTO'
        ]
    }

    try:
        # run the orchestrated multi-phase pipeline instead of the base crew
        result = ResellApp().run_full_pipeline(inputs)
        print(result)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        
        "image_urls": ['https://img.kleinanzeigen.de/api/v1/prod-ads/images/7c/7cd7b918-4651-4376-b020-6a2f79c37f51?rule=$_59.AUTO']
    }
    try:
        ResellApp().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ResellApp().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "image_urls": ['https://img.kleinanzeigen.de/api/v1/prod-ads/images/7c/7cd7b918-4651-4376-b020-6a2f79c37f51?rule=$_59.AUTO']
    }

    try:
        ResellApp().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


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
