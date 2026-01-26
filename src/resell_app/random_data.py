import os
import time
import random
import json
import shutil
import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import Field
from typing import ClassVar, Dict

class FastMarketSearch(BaseTool):
    name: str = "Fast_Market_Search"
    description: str = "Scrapes random items from specific electronics categories on Kleinanzeigen."
    
    # Input Fields
    output_folder: str = Field(default="Kleinanzeigen_Input", description="Root folder for saving data")
    
    # Constants
    BASE_URL: ClassVar[str] = "https://www.kleinanzeigen.de"
    
    HEADERS: ClassVar[Dict] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
    }

    TARGET_CATEGORIES: ClassVar[Dict] = {
        "Audio & HiFi": "/s-audio-hifi/c172",
        "Foto": "/s-fotografie/c245",
        "Handy & Telefon": "/s-handy-telekom/c173",
        "Haushaltsgeräte": "/s-haushaltsgeraete/c176",
        "Konsolen": "/s-konsolen/c279",
        "Notebooks": "/s-notebooks/c278",
        "PCs": "/s-pc/c228",
        "PC-Zubehör & Software": "/s-pc-zubehoer-software/c225",
        "Tablets & Reader": "/s-tablets-reader/c285",
        "TV & Video": "/s-tv-video/c175"
    }

    def _run(self, dummy_arg: str = "ignore") -> str:
        # Clean up previous run
        if os.path.exists(self.output_folder):
            shutil.rmtree(self.output_folder)
        
        images_path = os.path.join(self.output_folder, "images")
        os.makedirs(images_path, exist_ok=True)
        
        all_items = []
        total_cats = len(self.TARGET_CATEGORIES)
        
        print(f"--- Starting Scrape (Target: 20 random items per category) ---")
        
        # Simple loop with counts instead of progress bar
        for i, (cat_name, cat_slug) in enumerate(self.TARGET_CATEGORIES.items(), 1):
            print(f"[{i}/{total_cats}] Processing: {cat_name}...")
            
            category_items = self._scrape_category(cat_name, cat_slug)
            count = 0
            
            for item_link in category_items:
                item_data = self._process_single_item(item_link, cat_name, images_path)
                if item_data:
                    all_items.append(item_data)
                    count += 1
                
                time.sleep(random.uniform(0.5, 1.2))
            
            print(f"      -> Scraped {count} items.")

        # Saving as input_items.json inside Kleinanzeigen_Input
        json_path = os.path.join(self.output_folder, "input_items.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, indent=4, ensure_ascii=False)
            
        return f"Scraping finished. Saved {len(all_items)} items to {json_path}"

    def _scrape_category(self, name, slug):
        try:
            resp = requests.get(f"{self.BASE_URL}{slug}", headers=self.HEADERS, timeout=10)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            articles = soup.select('article.aditem')
            
            links = []
            for art in articles:
                link_tag = art.select_one('.aditem-main a')
                if link_tag and link_tag.get('href'):
                    links.append(self.BASE_URL + link_tag['href'])

            return random.sample(links, min(len(links), 20))
        except Exception as e:
            return []

    def _process_single_item(self, url, category, save_dir):
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            if resp.status_code != 200: return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            try: item_id = url.split('-')[-1]
            except: item_id = f"unknown_{int(time.time())}"

            title = soup.select_one('#viewad-title')
            price = soup.select_one('#viewad-price')
            desc = soup.select_one('#viewad-description-text')

            img_urls = []
            for img in soup.select('.galleryimage-element img'):
                src = img.get('data-src') or img.get('src')
                if src: img_urls.append(src)
            
            if not img_urls:
                main_img = soup.select_one('#viewad-image')
                if main_img:
                    src = main_img.get('src')
                    if src: img_urls.append(src)

            local_paths = []
            image_urls = []  # Store original URLs for workflow
            for idx, img_url in enumerate(img_urls):
                hq_url = img_url.replace("$_35.JPG", "$_59.JPG").replace("$_10.JPG", "$_59.JPG")
                image_urls.append(hq_url)  # Save original URL
                
                filename = f"{item_id}_{idx}.jpg"
                full_path = os.path.join(save_dir, filename)
                
                if self._download_image(hq_url, full_path):
                    # Using double backslashes for valid JSON on Windows
                    json_path = f"{self.output_folder}\\images\\{filename}"
                    local_paths.append(json_path)

            return {
                "id": item_id,
                "category": category,
                "title": title.text.strip() if title else "N/A",
                "price": price.text.strip() if price else "N/A",
                "description": desc.get_text(separator="\n").strip() if desc else "",
                "url": url,
                "image_urls": image_urls,
                "local_images": local_paths
            }
        except: return None

    def _download_image(self, url, path):
        try:
            r = requests.get(url, headers=self.HEADERS, stream=True, timeout=5)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                return True
        except: pass
        return False