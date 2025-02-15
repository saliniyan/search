import json
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from urllib.parse import quote

def setup_driver():
    """Initialize Firefox WebDriver with headless options."""
    options = Options()
    options.add_argument('--headless')  
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.set_preference('permissions.default.image', 1)
    return webdriver.Firefox(options=options)

def scroll_to_load_products(driver, max_scrolls=10):
    """Scroll the page to load more products."""
    last_height = driver.execute_script("return document.body.scrollHeight")

    for _ in range(max_scrolls):
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def extract_product_details(container):
    """Extract product details from a container."""
    product = {}
    try:
        product['name'] = container.find_element(By.CSS_SELECTOR, 'div[class*="novMV"], div[class*="styles_item"]').text.strip()
        product['image_url'] = container.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
        product['discount'] = container.find_element(By.CSS_SELECTOR, '[data-testid="item-offer-label-discount-text"]').text.strip() if container.find_elements(By.CSS_SELECTOR, '[data-testid="item-offer-label-discount-text"]') else "No discount"
        product['delivery_time'] = container.find_element(By.CSS_SELECTOR, 'div[class*="GOJ8s"]').text.strip() if container.find_elements(By.CSS_SELECTOR, 'div[class*="GOJ8s"]') else None
        product['weight'] = container.find_element(By.CSS_SELECTOR, 'div[class*="entQHA"]').text.strip() if container.find_elements(By.CSS_SELECTOR, 'div[class*="entQHA"]') else None

        price_element = container.find_element(By.CSS_SELECTOR, '[data-testid="itemOfferPrice"]') if container.find_elements(By.CSS_SELECTOR, '[data-testid="itemOfferPrice"]') else None
        product['new_price'] = float(price_element.text.replace('₹', '').replace(',', '').strip()) if price_element else None

        old_price_element = container.find_element(By.CSS_SELECTOR, '[data-testid="itemMRPPrice"]') if container.find_elements(By.CSS_SELECTOR, '[data-testid="itemMRPPrice"]') else None
        product['old_price'] = float(old_price_element.text.replace('₹', '').replace(',', '').strip()) if old_price_element else None

        product['in_stock'] = 'No' if container.find_elements(By.XPATH, ".//*[contains(text(), 'Out of stock') or contains(text(), 'Sold out')]") else 'Yes'
        product['is_advertisement'] = bool(container.find_elements(By.CSS_SELECTOR, '[data-testid="badge-wrapper"]'))
    except:
        return None
    return product

def scrape_product(product_name):
    """Scrape a specific product from Swiggy Instamart."""
    driver = setup_driver()
    products = []
    
    try:
        url = f"https://www.swiggy.com/instamart/search?location=chennai&custom_back=true&query={quote(product_name.replace(' ', '+'))}"
        driver.get(url)
        print(f"Scraping: {product_name}")

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="default_container_ux4"]'))
            )
        except:
            print(f"No results found for {product_name}")
            return []

        scroll_to_load_products(driver)
        product_containers = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="default_container_ux4"]')

        if not product_containers:
            print(f"No product containers found for: {product_name}")
            return []

        for container in product_containers[:20]:  # Limit to first 20 products
            product = extract_product_details(container)
            if product:
                product['category'] = product_name
                product['product_url'] = url
                product['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                products.append(product)

    finally:
        driver.quit()

    return products

def save_products(products, output_file):
    """Save scraped products to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape.py '<product_name>'")
        sys.exit(1)
    
    product_name = sys.argv[1]
    scraped_products = scrape_product(product_name)
    
    if scraped_products:
        save_products(scraped_products, f"/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/swiggy.json")
        print(f"Scraped {len(scraped_products)} products for '{product_name}'.")
    else:
        print(f"No products found for '{product_name}'.")
