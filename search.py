from flask import Flask, request, jsonify, render_template
import multiprocessing
import subprocess
import json
import os

app = Flask(__name__)

DATA_PATHS = {
    "bigbasket": "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/bigbasket.json",
    "blinkit": "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/blinkit.json",
    "swiggy": "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/swiggy.json",
}

def run_scraper(script, product_name):
    """Run a scraper script as a subprocess."""
    try:
        subprocess.run(["python", script, product_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script}: {e}")

@app.route("/", methods=["GET"])
def home():
    """Render the main search page."""
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    """Trigger scraping and return a status message."""
    product_name = request.form.get("product_name")
    if product_name:
        scripts = [
            "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/bigbasket.py",
            "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/blinkit.py",
            "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/swiggy.py",
        ]
        
        processes = [multiprocessing.Process(target=run_scraper, args=(script, product_name)) for script in scripts]

        for p in processes:
            p.start()

        for p in processes:
            p.join()

        return jsonify({"status": "Scraping started. Please wait..."}), 200

    return jsonify({"error": "No product name provided"}), 400

@app.route("/get_products", methods=["GET"])
def get_products():
    """Fetch scraped product data from the saved JSON files."""
    all_products = {}
    
    for platform, path in DATA_PATHS.items():
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as file:
                    products = json.load(file)
                    all_products[platform] = products
            except Exception as e:
                all_products[platform] = {"error": f"Failed to read data: {str(e)}"}
        else:
            all_products[platform] = {"error": "No data available"}
    
    return jsonify(all_products)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
