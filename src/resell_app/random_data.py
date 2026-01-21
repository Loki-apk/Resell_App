import os, time, random, json, requests, shutil
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import Field

class FastMarketSearch(BaseTool):
    name: str = "Fast_Market_Search"
    description: str = "Rapidly scrape 20 random items from 10 specific electronics categories on Kleinanzeigen using Requests."
    output_folder: str = Field(default="Kleinanzeigen_Data_Fast", description="Folder to save results")
    
    # Headers to mimic a real browser
    headers: dict = Field(default={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
    })

    def _run(self, dummy_arg: str = "ignore") -> str:
        # 1. CLEANUP & SETUP
        if os.path.exists(self.output_folder):
            shutil.rmtree(self.output_folder)
        
        img_dir = os.path.join(self.output_folder, "images")
        os.makedirs(img_dir, exist_ok=True)
        
        dataset = []
        base_url = "https://www.kleinanzeigen.de"
        
        categories = {
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

        print(f"--- Starting Fast Scrape (Target: 200 items) ---")

        # 2. CATEGORY LOOP
        for cat_name, cat_slug in categories.items():
            print(f"[*] Fetching Category: {cat_name}...")
            try:
                resp = requests.get(f"{base_url}{cat_slug}", headers=self.headers, timeout=10)
                if resp.status_code != 200:
                    print(f"    ! Skip: Status {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                ad_articles = soup.select('article.aditem')
                page_links = [base_url + a.select_one('.aditem-main a')['href'] 
                             for a in ad_articles if a.select_one('.aditem-main a')]
                
                # Sample 20 random items
                selected_links = random.sample(page_links, min(len(page_links), 20))
                print(f"    > Sampling {len(selected_links)} items...")

                # 3. ITEM DETAIL LOOP
                for i, link in enumerate(selected_links):
                    try:
                        time.sleep(random.uniform(0.7, 1.5)) # Safety delay
                        item_resp = requests.get(link, headers=self.headers, timeout=10)
                        if item_resp.status_code != 200: continue
                        
                        item_soup = BeautifulSoup(item_resp.text, 'html.parser')
                        item_id = link.split('/')[-1].split('-')[-1] if '-' in link else f"{cat_name}_{i}"
                        
                        # Data Extraction
                        title = item_soup.select_one('#viewad-title').text.strip() if item_soup.select_one('#viewad-title') else "N/A"
                        price = item_soup.select_one('#viewad-price').text.strip() if item_soup.select_one('#viewad-price') else "N/A"
                        desc = item_soup.select_one('#viewad-description-text').text.strip() if item_soup.select_one('#viewad-description-text') else ""
                        
                        # Images
                        img_urls = [img.get('data-src') or img.get('src') for img in item_soup.select('.galleryimage-element img')]
                        if not img_urls and item_soup.select_one('#viewad-image'):
                            img_urls = [item_soup.select_one('#viewad-image').get('src')]

                        local_images = []
                        for idx, url in enumerate(set(img_urls)):
                            hq_url = url.replace("$_35.JPG", "$_59.JPG").replace("$_10.JPG", "$_59.JPG")
                            path = self._download_image(hq_url, item_id, idx, img_dir)
                            if path: local_images.append(path)

                        dataset.append({
                            "id": item_id, "category": cat_name, "title": title,
                            "price": price, "description": desc, "url": link, "local_images": local_images
                        })
                    except: continue
            except Exception as e:
                print(f"Error in {cat_name}: {e}")

        # 4. SAVE
        with open(os.path.join(self.output_folder, "kleinanzeigen_items.json"), "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)
            
        return f"Scraped {len(dataset)} items to {self.output_folder}"

    def _download_image(self, url, item_id, idx, folder):
        try:
            res = requests.get(url, headers=self.headers, stream=True, timeout=5)
            if res.status_code == 200:
                path = os.path.join(folder, f"{item_id}_{idx}.jpg")
                with open(path, 'wb') as f:
                    shutil.copyfileobj(res.raw, f)
                return path
        except: pass
        return None

# --- CRITICAL: MUST BE OUTSIDE THE CLASS AT THE FAR LEFT ---
if __name__ == "__main__":
    tool = FastMarketSearch()
    print("Executing Scraper...")
    print(tool._run())