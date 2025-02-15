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
    options.set_preference('permissions.default.image', 2)
    return webdriver.Firefox(options=options)

def get_product_image(card):
    """Extract product image URL."""
    try:
        img_element = card.find_element(By.CSS_SELECTOR, "[data-testid='product-card-image']")
        return (
            img_element.get_attribute("srcset") or
            img_element.get_attribute("data-src") or
            img_element.get_attribute("src")
        )
    except:
        return None

def get_discount(card):
    """Extract discount details."""
    try:
        discount_element = card.find_element(By.CSS_SELECTOR, ".absolute.top-0.text-center.font-title.text-white")
        return discount_element.text.strip()
    except:
        return "No discount"

def get_stock_status(card):
    """Check if the product is in stock."""
    try:
        stock_element = card.find_elements(By.CLASS_NAME, "bg-opacity-50")
        return "No" if stock_element else "Yes"
    except:
        return "Unknown"

def get_product_link(card, driver):
    """Extract product link using JavaScript execution."""
    try:
        product_name = card.find_element(By.CSS_SELECTOR, "[data-testid='product-card-name']").text
        product_url = driver.execute_script(
            "return arguments[0].closest('a')?.href;", card
        )
        if not product_url:
            product_url = f"https://www.zeptonow.com/search?query={quote(product_name.replace(' ', '+'))}"
        return product_url
    except:
        return None

def extract_price_info(card):
    """Extract new and old prices."""
    try:
        new_price = card.find_element(By.CSS_SELECTOR, "[data-testid='product-card-price']").text
        try:
            old_price = card.find_element(By.CSS_SELECTOR, ".line-through").text
        except:
            old_price = None

        new_price = float(new_price.replace('₹', '').strip()) if new_price else None
        old_price = float(old_price.replace('₹', '').strip()) if old_price else None

        return new_price, old_price
    except:
        return None, None

def scroll_to_load_products(driver):
    """Scroll dynamically to load all products."""
    previous_height = 0
    while True:
        product_cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='product-card']")
        if not product_cards:
            break
        driver.execute_script("arguments[0].scrollIntoView();", product_cards[-1])
        time.sleep(2)
        if len(product_cards) == previous_height:
            break
        previous_height = len(product_cards)

def scrape_zepto_product(product_name):
    """Scrape details of a single product."""
    driver = setup_driver()
    products = []

    try:
        url = f"https://www.zeptonow.com/search?query={quote(product_name.replace(' ', '+'))}"
        driver.get(url)
        print(f"Scraping: {product_name}")

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='product-card']"))
            )
        except:
            print(f"No results found for {product_name}")
            return []

        scroll_to_load_products(driver)
        product_cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='product-card']")

        if not product_cards:
            print(f"No products found for {product_name}")
            return []

        for card in product_cards[:20]:  # Limit to first 60 results
            try:
                new_price, old_price = extract_price_info(card)

                product = {
                    'category': product_name,
                    'name': card.find_element(By.CSS_SELECTOR, "[data-testid='product-card-name']").text,
                    'image_url': get_product_image(card),
                    'product_url': get_product_link(card, driver),
                    'quantity': card.find_element(By.CSS_SELECTOR, "[data-testid='product-card-quantity']").text,
                    'new_price': new_price,
                    'old_price': old_price,
                    'discount': get_discount(card),
                    'in_stock': get_stock_status(card)
                }

                products.append(product)

            except:
                continue

    finally:
        driver.quit()

    return products

def save_products(products, output_file):
    """Save products to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: No product name provided.")
        sys.exit(1)

    product_name = sys.argv[1]  # Get the single product name
    scraped_data = scrape_zepto_product(product_name)
    save_products(scraped_data, "/search/zepto_output.json")

    print(f"Scraped {len(scraped_data)} products for '{product_name}'. Data saved in 'zepto_output.json'.")
