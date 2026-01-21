import os, requests, base64, json
from typing import Type, List, Union
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from openai import OpenAI

class MultiImageToolInput(BaseModel):
    image_urls: Union[List[str], str] = Field(..., description="List of image URLs or single URL string.")

class QwenVisionTool(BaseTool):
    name: str = "Qwen Vision Tool"
    description: str = "Forensic analysis of product images to ensure consistency and extract details (Name, Model, Condition)."
    args_schema: Type[BaseModel] = MultiImageToolInput

    def _run(self, image_urls: Union[List[str], str]) -> str:
        # 1. Sanitize Input
        if isinstance(image_urls, str):
            try: image_urls = json.loads(image_urls)
            except: image_urls = [u.strip() for u in image_urls.split(',')]
            
        # 2. Build Payload
        content = [{"type": "text", "text": "Analyze images. 1. Check consistency (same object?). 2. Extract: Item Name, Model, Color, Condition. OUTPUT JSON ONLY: {status: 'SUCCESS'|'ERROR', item_name, model, color, condition, description, reason(if error)}."}]
        
        for url in image_urls:
            try:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    b64 = base64.b64encode(res.content).decode('utf-8')
                    content.append({"type": "image_url", "image_url": {"url": f"data:{res.headers.get('Content-Type', 'image/jpeg')};base64,{b64}"}})
            except: pass

        if len(content) == 1: return "ERROR: No accessible images found."

        # 3. Call LLM
        try:
            client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=os.getenv("Image_MODEL"),
                messages=[{"role": "user", "content": content}],
                temperature=0.0
            )
            # Just clean markdown and return. The Agent will parse the JSON string.
            return response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        except Exception as e: return f"ERROR: {str(e)}"