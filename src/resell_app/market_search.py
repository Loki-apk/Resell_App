import os, time, random, json, requests, shutil
import undetected_chromedriver as uc
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crewai.tools import BaseTool
from pydantic import Field

class MarketSearch(BaseTool):
    name: str = "Market_Search"
    description: str = "Search and scrape item details from Kleinanzeigen.de."
    output_folder: str = Field(default="Kleinanzeigen_Data", description="Folder to save results")

    def _run(self, search_query: str = "elektronik", min_items: int = 20) -> str:
        # Use absolute path for consistency
        # Path(__file__).parent = src/resell_app
        # Path(__file__).parent.parent = src
        # Path(__file__).parent.parent.parent = root project folder
        abs_output_folder = Path(__file__).parent.parent.parent / self.output_folder
        print(f"DEBUG: __file__ = {__file__}")
        print(f"DEBUG: abs_output_folder = {abs_output_folder}")
        
        # 1. CLEANUP
        if abs_output_folder.exists(): 
            shutil.rmtree(abs_output_folder)
        
        # 2. SETUP
        min_items = max(5, min_items)
        img_dir = abs_output_folder / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        
        # --- SPEED OPTIMIZATIONS ---
        options = uc.ChromeOptions()
        options.page_load_strategy = 'eager' # Don't wait for full page load
        
        # Disable image RENDERING in browser (speed up navigation)
        # We will still download the files manually below.
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        driver = uc.Chrome(options=options, version_main=142)
        dataset, item_links = [], set()
        
        try:
            print(f"--- Scraping '{search_query}' (Target: {min_items}) ---")
            driver.get(f"https://www.kleinanzeigen.de/s-{search_query.replace(' ', '-')}/k0")
            
            # 3. Cookie Consent (Fast Check)
            try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "gdpr-banner-accept"))).click()
            except: pass

            # 4. Collect Links
            while len(item_links) < min_items:
                try:
                    WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article.aditem")))
                    elems = driver.find_elements(By.CSS_SELECTOR, "article.aditem .aditem-main a")
                    new_links = {e.get_attribute("href") for e in elems if "/s-anzeige/" in e.get_attribute("href")}
                    item_links.update(new_links)
                    
                    if len(item_links) >= min_items or not new_links: break
                    
                    btn = driver.find_element(By.CLASS_NAME, "pagination-next")
                    driver.execute_script("arguments[0].scrollIntoView();", btn)
                    btn.click()
                    time.sleep(random.uniform(1.5, 2.5))
                except: break

            print(f"Collected {len(item_links)} links. Starting extraction...")

            # 5. Extract Details & DOWNLOAD IMAGES
            target_links = list(item_links)[:min_items]
            
            for i, link in enumerate(target_links):
                try:
                    driver.get(link)
                    time.sleep(random.uniform(0.8, 1.5)) 
                    
                    item_id = link.split('/')[-1].split('-')[-1] if '-' in link else f"item_{i}"
                    
                    # Text Helpers
                    getText = lambda x: driver.find_element(By.ID, x).text.strip() if driver.find_elements(By.ID, x) else "N/A"
                    
                    # Image URL Extraction
                    imgs = [e.get_attribute("data-src") or e.get_attribute("src") for e in driver.find_elements(By.CSS_SELECTOR, ".galleryimage-element img")]
                    if not imgs and driver.find_elements(By.CSS_SELECTOR, "#viewad-image"):
                        imgs = [driver.find_element(By.CSS_SELECTOR, "#viewad-image").get_attribute("src")]
                    
                    # --- IMAGE DOWNLOADING ---
                    local_images_paths = []
                    for idx, url in enumerate(set(imgs)):
                        if url:
                            hq_url = url.replace("$_35.JPG", "$_59.JPG").replace("$_57.JPG", "$_59.JPG")
                            
                            # Define paths
                            filename = f"{item_id}_{idx}.jpg"
                            full_save_path = img_dir / filename
                            
                            # Download the file
                            if self._download_image(hq_url, str(full_save_path)):
                                # Format for JSON: "Kleinanzeigen_Data\\images\\123_0.jpg"
                                json_path_str = f"{self.output_folder}\\images\\{filename}"
                                local_images_paths.append(json_path_str)

                    dataset.append({
                        "id": item_id, 
                        "title": getText("viewad-title"), 
                        "price": getText("viewad-price"),
                        "description": getText("viewad-description-text"), 
                        "url": link, 
                        "local_images": local_images_paths
                    })
                    print(f"[{i+1}/{len(target_links)}] Scraped & Downloaded: {item_id}")
                    
                except Exception as e: print(f"Error {link}: {e}")

            # 6. Save Data
            json_file = abs_output_folder / "kleinanzeigen_items.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=4, ensure_ascii=False)
            
            return f"Successfully scraped {len(dataset)} items. Images saved to {img_dir}"

        except Exception as e: return f"Error: {str(e)}"
        finally: driver.quit()

    def _download_image(self, url, save_path):
        """Downloads image using Requests (bypassing Selenium rendering)"""
        try:
            # Use a standard header so the image server accepts the request
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, stream=True, timeout=5)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    shutil.copyfileobj(res.raw, f)
                return True
        except: pass
        return False
