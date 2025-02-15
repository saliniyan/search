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
    firefox_options.add_argument('--disable-gpu')
    firefox_options.add_argument('--no-sandbox')
    firefox_options.add_argument('--disable-dev-shm-usage')
    firefox_options.set_preference('permissions.default.image', 2)
    return webdriver.Firefox(options=firefox_options)

def get_product_image(card):
    try:
        return card.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
    except:
        return None

def get_stock_status(card):
    try:
        return "No" if card.find_elements(By.CSS_SELECTOR, "div.bg-opacity-50") else "Yes"
    except:
        return "Unknown"

def get_ratings_info(card):
    try:
        ratings_div = card.find_element(By.CLASS_NAME, "ReviewsAndRatings___StyledDiv-sc-2rprpc-0")
        rating = float(ratings_div.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.Badges___StyledLabel-sc-1k3p1ug-0 span").text)
        review_count = ratings_div.find_element(By.CLASS_NAME, "ReviewsAndRatings___StyledLabel-sc-2rprpc-1").text
        return {'rating': rating, 'review_count': review_count}
    except:
        return {'rating': 0.0, 'review_count': "0 Ratings"}

def extract_price_info(card):
    try:
        price_div = card.find_element(By.CLASS_NAME, "Pricing___StyledDiv-sc-pldi2d-0")
        new_price = float(price_div.find_element(By.CLASS_NAME, "Pricing___StyledLabel-sc-pldi2d-1").text.replace('₹', '').strip())
        try:
            old_price = float(price_div.find_element(By.CLASS_NAME, "Pricing___StyledLabel2-sc-pldi2d-2").text.replace('₹', '').strip())
        except:
            old_price = None
        return new_price, old_price
    except:
        return None, None

def extract_discount(card):
    try:
        return card.find_element(By.CSS_SELECTOR, "span.font-semibold.leading-xxl").text.strip()
    except:
        return "No discount"

def scroll_to_load_products(driver):
    """Scroll dynamically to load all products."""
    previous_height = 0
    while True:
        product_cards = driver.find_elements(By.CLASS_NAME, "SKUDeck___StyledDiv-sc-1e5d9gk-0")
        if not product_cards:
            break
        driver.execute_script("arguments[0].scrollIntoView();", product_cards[-1])
        time.sleep(2)
        if len(product_cards) == previous_height:
            break
        previous_height = len(product_cards)

def get_weight(card):
    """Extract the weight of the product."""
    try:
        weight_element = card.find_element(By.CSS_SELECTOR, "span.PackChanger___StyledLabel-sc-newjpv-1")
        return weight_element.text.strip()
    except:
        return None
    
def scrape_bigbasket_products(product_name):
    driver = setup_driver()
    products = []

    try:
        url = f"https://www.bigbasket.com/ps/?q={quote(product_name.replace(' ', '+'))}&nc=as"
        driver.get(url)
        print(f"Scraping: {product_name}")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "SKUDeck___StyledDiv-sc-1e5d9gk-0"))
            )
        except:
            print("No products found.")
            return []

        scroll_to_load_products(driver)
        product_cards = driver.find_elements(By.CLASS_NAME, "SKUDeck___StyledDiv-sc-1e5d9gk-0")

        if not product_cards:
            print("No products available.")
            return []

        for card in product_cards[:20]:  # Scraping only first 40 products
            try:
                new_price, old_price = extract_price_info(card)
                product = {
                    'category': product_name,
                    'brand': card.find_element(By.CLASS_NAME, "BrandName___StyledLabel2-sc-hssfrl-1").text,
                    'name': card.find_element(By.CSS_SELECTOR, "h3.line-clamp-2").text,
                    'image_url': get_product_image(card),
                    'in_stock': get_stock_status(card),
                    'new_price': new_price,
                    'old_price': old_price,
                    'discount': extract_discount(card),
                    'pack_size': None,
                    'special_offer': None,
                    'product_url': None,
                    'weight': get_weight(card)  # Add weight here
                }

                try:
                    product['product_url'] = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                except:
                    pass

                try:
                    product['pack_size'] = card.find_element(By.CLASS_NAME, "PackSelector___StyledLabel-sc-1lmu4hv-0").text.strip()
                except:
                    pass

                try:
                    product['special_offer'] = card.find_element(By.CLASS_NAME, "OfferCommunication___StyledDiv-sc-zgmi5i-0").text.strip()
                except:
                    pass

                product.update(get_ratings_info(card))
                products.append(product)

            except Exception as e:
                print(f"Error scraping product: {e}")
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
    scraped_products = scrape_bigbasket_products(product_name)
    
    if scraped_products:
        save_products(scraped_products, f"/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/bigbasket.json")
        print(f"Scraped {len(scraped_products)} products for '{product_name}'.")
    else:
        print(f"No products found for '{product_name}'.")