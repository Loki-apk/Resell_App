import os
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from resell_app.tools.vision_tool import QwenVisionTool
from resell_app.tools.metrics_tools import EvaluationMetricsTool
from resell_app.tools.file_read_tool import UTF8FileReadTool
from resell_app.market_search import MarketSearch

load_dotenv()

# Global LLM Setup
BASE_CFG = {"base_url": os.getenv("OPENAI_BASE_URL"), "api_key": os.getenv("OPENAI_API_KEY")}
VIS_LLM = LLM(model=os.getenv("Image_MODEL"), temperature=0.0, **BASE_CFG)
TXT_LLM = LLM(model=os.getenv("MODEL"), temperature=0.1, **BASE_CFG)

@CrewBase
class ResellApp:
    """ResellApp crew definitions"""
    
    # Tools
    vision_tool = QwenVisionTool()
    metrics_tool = EvaluationMetricsTool()
    file_reader_tool = UTF8FileReadTool(file_path="C:\\Sem_1_Project\\Resell App\\src\\Kleinanzeigen_Data\\kleinanzeigen_items.json") 

    # Market Search Integration
    market_search = MarketSearch()


    @agent
    def image_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["image_analyzer"],
            verbose=True,  
            tools=[self.vision_tool],
            llm=VIS_LLM
        )
    
    @agent
    def search_query_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["search_query_generator"],
            verbose=True,  
            llm=TXT_LLM
        )
    
    @agent
    def search_list_evaluator(self) -> Agent:
        return Agent(
            config=self.agents_config["search_list_evaluator"],
            verbose=True,  
            tools=[self.file_reader_tool, self.metrics_tool],
            llm=TXT_LLM
        )
    
    # --- TASKS ---
    @task
    def image_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["image_analysis_task"],
            agent=self.image_analyzer(),
            output_file="image_analysis.json"
        )
    
    @task
    def generate_query_task(self) -> Task:
        return Task(
            config=self.tasks_config["generate_query_task"],
            agent=self.search_query_generator(),
            output_file="search_query.json"
        )
    
    @task
    def evaluate_list_task(self) -> Task:
        return Task(
            config=self.tasks_config["evaluate_list_task"],
            agent=self.search_list_evaluator(),
            output_file="query_evaluation.json",
            async_execution=True
        )
    
   
    @crew
    def analysis_and_query_crew(self) -> Crew:
        return Crew(
            agents=[self.image_analyzer(), self.search_query_generator()],
            tasks=[self.image_analysis_task(), self.generate_query_task()],
            process=Process.sequential,
            verbose=True 
        )
    
    @crew
    def query_regeneration_crew(self) -> Crew:
        return Crew(
            agents=[self.search_query_generator()],
            tasks=[self.generate_query_task()],
            process=Process.sequential,
            verbose=True
        )
    
    @crew
    def evaluation_crew(self) -> Crew:
        return Crew(
            agents=[self.search_list_evaluator()],
            tasks=[self.evaluate_list_task()],
            process=Process.sequential,
            verbose=True
        )

    def run_full_pipeline(self, inputs: dict):
        from resell_app.workflow import ResellWorkflow
        return ResellWorkflow(self).run(inputs)