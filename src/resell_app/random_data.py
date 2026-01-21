import os, time, random, json, requests, shutil
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import Field

class FastMarketSearch(BaseTool):
    name: str = "Fast_Market_Search"
    description: str = "Rapidly scrape 20 random items from 10 specific electronics categories on Kleinanzeigen using Requests."
    output_folder: str = Field(default="Kleinanzeigen_Data_Fast", description="Folder to save results")
    
    # Headers are crucial for 'requests' to look like a real browser
    headers: dict = Field(default={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
    }, description="HTTP Headers")

    def _run(self, dummy_arg: str = "ignore") -> str:
        # 1. CLEANUP
        if os.path.exists(self.output_folder):
            shutil.rmtree(self.output_folder)
        
        img_dir = os.path.join(self.output_folder, "images")
        os.makedirs(img_dir, exist_ok=True)
        
        dataset = []
        
        # The 10 specific categories
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
        base_url = "https://www.kleinanzeigen.de"

        # 2. CATEGORY LOOP
        for cat_name, cat_slug in categories.items():
            print(f"[*] Fetching Category: {cat_name}...")
            
            try:
                # Get Category Page
                resp = requests.get(f"{base_url}{cat_slug}", headers=self.headers)
                if resp.status_code != 200:
                    print(f"    ! Failed to load category (Status: {resp.status_code})")
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Extract Links
                ad_articles = soup.select('article.aditem')
                page_links = []
                for ad in ad_articles:
                    link_tag = ad.select_one('.aditem-main a')
                    if link_tag and link_tag.get('href'):
                        full_link = base_url + link_tag.get('href')
                        page_links.append(full_link)
                
                # Random Sample of 20
                target_count = 20
                if len(page_links) < target_count:
                    selected_links = page_links
                else:
                    selected_links = random.sample(page_links, target_count)
                
                print(f"    > Found {len(page_links)} items. Sampling {len(selected_links)}...")

                # 3. ITEM DETAIL LOOP
                for i, link in enumerate(selected_links):
                    try:
                        # Polite delay (0.5 - 1.5s) is enough for requests usually
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        item_resp = requests.get(link, headers=self.headers)
                        if item_resp.status_code != 200: continue
                        
                        item_soup = BeautifulSoup(item_resp.text, 'html.parser')
                        
                        # ID Generation
                        item_id = link.split('/')[-1].split('-')[-1] if '-' in link else f"{cat_name}_{i}"
                        
                        # Data Extraction
                        title_tag = item_soup.select_one('#viewad-title')
                        title = title_tag.text.strip() if title_tag else "N/A"
                        
                        price_tag = item_soup.select_one('#viewad-price')
                        price = price_tag.text.strip() if price_tag else "N/A"
                        
                        desc_tag = item_soup.select_one('#viewad-description-text')
                        description = desc_tag.text.strip() if desc_tag else ""
                        
                        # Image Extraction
                        # Kleinanzeigen puts images in a gallery or single featured image
                        img_urls = []
                        
                        # Case A: Gallery
                        gallery_imgs = item_soup.select('.galleryimage-element img')
                        for img in gallery_imgs:
                            src = img.get('data-src') or img.get('src')
                            if src: img_urls.append(src)
                            
                        # Case B: Single Image (if gallery empty)
                        if not img_urls:
                            single_img = item_soup.select_one('#viewad-image')
                            if single_img:
                                src = single_img.get('data-src') or single_img.get('src')
                                if src: img_urls.append(src)
                        
                        # Download Images
                        local_images = []
                        for idx, url in enumerate(set(img_urls)):
                            # Convert thumbnail URL to High Res
                            hq_url = url.replace("$_35.JPG", "$_59.JPG").replace("$_57.JPG", "$_59.JPG").replace("$_10.JPG", "$_59.JPG")
                            
                            saved_path = self._download_image(hq_url, item_id, idx, img_dir)
                            if saved_path:
                                local_images.append(saved_path)

                        dataset.append({
                            "id": item_id,
                            "category": cat_name,
                            "title": title,
                            "price": price,
                            "description": description,
                            "url": link,
                            "local_images": local_images
                        })

                    except Exception as e:
                        print(f"    ! Error on item {link}: {e}")
                        continue
                        
            except Exception as e:
                print(f"    ! Error on category {cat_name}: {e}")

        # 4. SAVE DATA
        json_path = os.path.join(self.output_folder, "kleinanzeigen_items.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)
            
        return f"Completed. Scraped {len(dataset)} items. Data saved to '{self.output_folder}'."

    def _download_image(self, url, item_id, idx, folder):
        try:
            # Short timeout for images to keep things moving
            res = requests.get(url, headers=self.headers, stream=True, timeout=3)
            if res.status_code == 200:
                safe_id = "".join([c for c in item_id if c.isalnum() or c in ('-','_')])
                filename = f"{safe_id}_{idx}.jpg"
                path = os.path.join(folder, filename)
                
                with open(path, 'wb') as f:
                    res.raw.decode_content = True
                    shutil.copyfileobj(res.raw, f)
                return path
        except:
            pass
        return None
    
    if __name__ == "__main__":
    # Initialize the tool
    tool = FastMarketSearch()
    
    # Run the scraping function
    print("Starting execution...")
    result = tool._run()
    
    # Print the final summary
    print(result)