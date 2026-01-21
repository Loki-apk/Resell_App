import os, time, random, json, requests, shutil
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crewai.tools import BaseTool
from pydantic import Field

class MarketSearch(BaseTool):
    name: str = "Market_Search"
    description: str = "Search and scrape item details from Kleinanzeigen.de."
    output_folder: str = Field(default="Kleinanzeigen_Data", description="Folder to save results")

    def _run(self, search_query: str, min_items: int = 20) -> str:
        # 1. CLEANUP: Wipe previous data (images & json)
        if os.path.exists(self.output_folder): shutil.rmtree(self.output_folder)
        
        # 2. SETUP
        min_items = max(5, min_items)
        img_dir = os.path.join(self.output_folder, "images")
        os.makedirs(img_dir, exist_ok=True)
        
        driver = uc.Chrome(options=uc.ChromeOptions(), version_main=142)
        dataset, item_links = [], set()
        
        try:
            print(f"--- Scraping '{search_query}' (Target: {min_items}) ---")
            driver.get(f"https://www.kleinanzeigen.de/s-{search_query.replace(' ', '-')}/k0")
            
            # 3. Cookie Consent
            try: WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "gdpr-banner-accept"))).click()
            except: pass

            # 4. Collect Links
            while len(item_links) < min_items:
                try:
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article.aditem")))
                    elems = driver.find_elements(By.CSS_SELECTOR, "article.aditem .aditem-main a")
                    new_links = {e.get_attribute("href") for e in elems if "/s-anzeige/" in e.get_attribute("href")}
                    item_links.update(new_links)
                    
                    if len(item_links) >= min_items or not new_links: break
                    
                    btn = driver.find_element(By.CLASS_NAME, "pagination-next")
                    driver.execute_script("arguments[0].scrollIntoView();", btn)
                    btn.click()
                    time.sleep(random.uniform(2, 4))
                except: break

            # 5. Extract Details
            for i, link in enumerate(list(item_links)[:min_items]):
                try:
                    driver.get(link)
                    time.sleep(random.uniform(1.5, 3))
                    item_id = link.split('/')[-1].split('-')[-1] if '-' in link else f"item_{i}"
                    
                    # Helpers
                    getText = lambda x: driver.find_element(By.ID, x).text.strip() if driver.find_elements(By.ID, x) else "N/A"
                    
                    # Images
                    imgs = [e.get_attribute("data-src") or e.get_attribute("src") for e in driver.find_elements(By.CSS_SELECTOR, ".galleryimage-element img")]
                    if not imgs and driver.find_elements(By.CSS_SELECTOR, "#viewad-image"):
                        imgs = [driver.find_element(By.CSS_SELECTOR, "#viewad-image").get_attribute("src")]
                    
                    saved_imgs = []
                    for idx, url in enumerate(set(imgs)):
                        if url:
                            hq_url = url.replace("$_35.JPG", "$_59.JPG").replace("$_57.JPG", "$_59.JPG")
                            path = self._save_img(hq_url, item_id, idx, img_dir)
                            if path: saved_imgs.append(path)

                    dataset.append({
                        "id": item_id, "title": getText("viewad-title"), "price": getText("viewad-price"),
                        "description": getText("viewad-description-text"), "url": link, "local_images": saved_imgs
                    })
                except Exception as e: print(f"Error {link}: {e}")

            # 6. Save Data
            with open(os.path.join(self.output_folder, "kleinanzeigen_items.json"), "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=4, ensure_ascii=False)
            
            return json.dumps([{"title": i['title'], "price": i['price'], "link": i['url']} for i in dataset], ensure_ascii=False)

        except Exception as e: return f"Error: {str(e)}"
        finally: driver.quit()

    def _save_img(self, url, item_id, idx, folder):
        try:
            res = requests.get(url, stream=True, timeout=5)
            if res.status_code == 200:
                path = os.path.join(folder, f"{item_id}_{idx}.jpg")
                with open(path, 'wb') as f: f.write(res.content)
                return path
        except: pass
        return None