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
    firefox_options = Options()
    firefox_options.add_argument('--headless')
    firefox_options.set_preference('permissions.default.image', 2)
    return webdriver.Firefox(options=firefox_options)

def get_high_quality_image(card):
    """Extract high-quality product image from the card."""
    try:
        image_element = card.find_element(By.CSS_SELECTOR, "img")
        return (
            image_element.get_attribute("srcset") or
            image_element.get_attribute("data-src") or
            image_element.get_attribute("src")
        )
    except:
        return None

def get_stock_status(card):
    """Check if product is in stock."""
    try:
        out_of_stock = len(card.find_elements(By.CLASS_NAME, "AddToCart__UpdatedOutOfStockTag-sc-17ig0e3-4")) > 0
        return 'No' if out_of_stock else 'Yes'
    except:
        return "Unknown"

def extract_price_info(price_container):
    """Extract new and old prices from price container."""
    try:
        price_elements = price_container.find_elements(By.CSS_SELECTOR, "div[style*='color']")
        new_price, old_price = "", ""
        
        for price in price_elements:
            style = price.get_attribute('style')
            if 'text-decoration-line: line-through' in style:
                old_price = price.text.replace('₹', '').strip()
            elif 'color: rgb(31, 31, 31)' in style:
                new_price = price.text.replace('₹', '').strip()
        
        return float(new_price) if new_price else None, float(old_price) if old_price else None
    except:
        return None, None

def calculate_discount(new_price, old_price):
    """Calculate discount percentage."""
    try:
        if old_price and new_price:
            discount = ((old_price - new_price) / old_price) * 100
            return f"{round(discount)}%"
    except:
        pass
    return "No discount"

def scroll_to_load_products(driver):
    """Scroll page to load more products."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def scrape_product(product_name):
    """Scrape details for a specific product."""
    driver = setup_driver()
    products = []
    
    try:
        url = f"https://blinkit.com/s/?q={quote(product_name.replace(' ', '+'))}"
        driver.get(url)
        print(f"Scraping: {product_name}")

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Product__UpdatedDetailContainer-sc-11dk8zk-5"))
            )
        except:
            print("No products found.")
            return []

        scroll_to_load_products(driver)
        product_cards = driver.find_elements(By.CSS_SELECTOR, "a[data-test-id='plp-product']")

        if not product_cards:
            print("No products available.")
            return []

        for card in product_cards[:20]:  # Limit to first 20 products
            try:
                price_container = card.find_element(By.CLASS_NAME, "Product__UpdatedPriceAndAtcContainer-sc-11dk8zk-10")
                new_price, old_price = extract_price_info(price_container)

                product = {
                    'name': card.find_element(By.CLASS_NAME, "Product__UpdatedTitle-sc-11dk8zk-9").text,
                    'image_url': get_high_quality_image(card),
                    'product_url': card.get_attribute('href'),
                    'weight': card.find_element(By.CLASS_NAME, "bff_variant_text_only").text,
                    'new_price': new_price,
                    'old_price': old_price,
                    'discount': calculate_discount(new_price, old_price),
                    'in_stock': get_stock_status(card),
                    'special_offer': None
                }

                # Get special offer if available
                try:
                    product['special_offer'] = card.find_element(By.CLASS_NAME, "OfferTag__StyledOfferTag-sc-1p5qqkx-0").text
                except:
                    pass

                products.append(product)

            except Exception as e:
                continue

    except Exception as e:
        print(f"Error: {e}")
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
        save_products(scraped_products, f"/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/blinkit.json")
        print(f"Scraped {len(scraped_products)} products for '{product_name}'.")
    else:
        print(f"No products found for '{product_name}'.")
