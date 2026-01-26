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
            try: 
                image_urls = json.loads(image_urls)
            except: 
                image_urls = [u.strip() for u in image_urls.split(',') if u.strip()]
        
        # Ensure it's a list
        if not isinstance(image_urls, list):
            return json.dumps({"status": "ERROR", "reason": "image_urls must be a list"})
        
        # 2. Limit to 4 images maximum
        if len(image_urls) == 0:
            return json.dumps({"status": "ERROR", "reason": "No image URLs provided"})
        
        image_urls = image_urls[:4]
        
        # 3. Build Payload
        content = [{"type": "text", "text": "Analyze images. 1. Check consistency (same object?). 2. Extract: Item Name, Model, Color, Condition. OUTPUT JSON ONLY: {status: 'SUCCESS'|'ERROR', item_name, model, color, condition, description, reason(if error)}."}]
        
        for url in image_urls:
            try:
                image_data = None
                content_type = "image/jpeg"
                
                # Handle local file paths (with or without backslashes)
                if url.startswith("Kleinanzeigen") or url.startswith("."):
                    # Convert Windows paths to forward slashes for compatibility
                    local_path = url.replace("\\", "/")
                    if os.path.exists(local_path):
                        with open(local_path, 'rb') as f:
                            image_data = f.read()
                        # Detect content type from file extension
                        if local_path.lower().endswith('.png'):
                            content_type = "image/png"
                # Handle HTTP/HTTPS URLs
                elif url.startswith('http'):
                    res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                    if res.status_code == 200:
                        image_data = res.content
                        content_type = res.headers.get('Content-Type', 'image/jpeg')
                
                # If we got image data, encode and add to content
                if image_data:
                    b64 = base64.b64encode(image_data).decode('utf-8')
                    content.append({"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{b64}"}})
            except Exception as e:
                pass

        if len(content) == 1: 
            return json.dumps({"status": "ERROR", "reason": "No accessible images found"})

        # 4. Call LLM
        try:
            client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=os.getenv("Image_MODEL"),
                messages=[{"role": "user", "content": content}],
                temperature=0.0
            )
            result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            # Validate it's valid JSON before returning
            try:
                json.loads(result)
                return result
            except:
                return json.dumps({"status": "ERROR", "reason": f"Invalid JSON response from model: {result[:100]}"})
        except Exception as e: 
            return json.dumps({"status": "ERROR", "reason": str(e)[:200]})