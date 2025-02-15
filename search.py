from flask import Flask, request, jsonify, render_template
import multiprocessing
import subprocess
import json
import os
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.graph_objects as go

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
    except Exception as e:
        print(f"Unexpected error running {script}: {e}")

@app.route("/", methods=["GET"])
def home():
    """Render the main search page."""
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    """Trigger scraping and return a status message."""
    product_name = request.form.get("product_name")
    if not product_name:
        return jsonify({"error": "No product name provided"}), 400

    scripts = [
        "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/bigbasket.py",
        "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/blinkit.py",
        "/home/saliniyan/Documents/git_project/e-commerce/e-commerce-web-scarpping/new/search/swiggy.py",
    ]

    try:
        processes = [
            multiprocessing.Process(target=run_scraper, args=(script, product_name))
            for script in scripts
        ]
        
        for p in processes:
            p.start()
        
        for p in processes:
            p.join(timeout=30)  # Add timeout to prevent hanging
            
        return jsonify({"status": "Scraping started. Please wait..."}), 200
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

@app.route("/get_products", methods=["GET"])
def get_products():
    """Fetch scraped product data from the saved JSON files."""
    all_products = {}
    
    for platform, path in DATA_PATHS.items():
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    products = json.load(file)
                    all_products[platform] = products
            else:
                all_products[platform] = {"error": "No data available"}
        except json.JSONDecodeError as e:
            all_products[platform] = {"error": f"Invalid JSON data: {str(e)}"}
        except Exception as e:
            all_products[platform] = {"error": f"Failed to read data: {str(e)}"}
    
    return jsonify(all_products)

@app.route("/products", methods=["GET"])
def products_page():
    """Render a page that shows all the products and allows selection."""
    all_products = {}
    
    for platform, path in DATA_PATHS.items():
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    products = json.load(file)
                    all_products[platform] = products
            else:
                all_products[platform] = []
        except Exception as e:
            print(f"Error loading products for {platform}: {e}")
            all_products[platform] = []
    
    return render_template("products.html", all_products=all_products)

def get_product_by_id(product_id, data_paths):
    """Fetch product details from JSON files by product ID."""
    for platform, path in data_paths.items():
        try:
            with open(path, 'r', encoding='utf-8') as file:
                products = json.load(file)
                for product in products:
                    if str(product.get('id')) == str(product_id):
                        product['platform'] = platform.capitalize()
                        return product
        except Exception as e:
            print(f"Error reading {platform} data: {e}")
    return None

@app.route("/submit_selected_products", methods=["POST"])
def submit_selected_products():
    """Handle the selected products from the form and send to dashboard."""
    selected_products_data = request.form.getlist('selected_products')
    
    if not selected_products_data:
        return render_template("dashboard.html", selected_products=[], recommended_product=None, price_plot_html="", discount_plot_html="", stock_plot_html="")
    
    selected_products = []
    invalid_products = []

    # Lists to store data for plots
    product_names = []
    prices = []  # This will store the original prices for the product list
    unit_prices = []  # This will store the calculated unit prices for the dashboard
    discounts = []
    in_stock_counts = {"In Stock": 0, "Out of Stock": 0}
    
    # Recommendation criteria
    recommended_product = None
    
    # Process each product's data
    for product_data in selected_products_data:
        product_details = product_data.split('|')
        
        if len(product_details) >= 6:
            try:
                # Calculate price per unit by dividing by weight
                price = float(product_details[1].replace('₹', '').replace(',', ''))  # Clean price
                weight_str = product_details[3]
                weight = float(weight_str.split()[0]) if weight_str.split()[0].replace('.', '', 1).isdigit() else 1.0  # Default to 1.0 if invalid
                unit = weight_str.split()[1] if len(weight_str.split()) > 1 else 'kg'  # Default to kg if no unit provided

                # Calculate price per unit based on weight
                price_per_unit = price / weight if weight > 0 else price  # Avoid division by zero

                product = {
                    "name": product_details[0],
                    "original_price": price,  # Store the original price here
                    "new_price": price_per_unit,  # Price per unit for the dashboard
                    "discount": 0,
                    "weight": weight,
                    "unit": unit,
                    "in_stock": product_details[5] == 'True'
                }
                
                # Clean the discount string (remove '%' and 'OFF')
                discount_str = product_details[2].replace('%', '').replace(',', '').strip()

                # Check if the discount is valid (numeric or percentage)
                product['discount'] = float(discount_str) if discount_str.replace('.', '', 1).isdigit() else 0
                
                selected_products.append(product)

                # Add to plot data
                product_names.append(product['name'])
                prices.append(product['original_price'])  # Use the original price for the list
                unit_prices.append(product['new_price'])  # Use unit price for the dashboard
                discounts.append(product['discount'])
                if product['in_stock']:
                    in_stock_counts["In Stock"] += 1
                else:
                    in_stock_counts["Out of Stock"] += 1
                
                # Recommendation logic: Choose one product with the best discount or lowest price per unit
                if recommended_product is None or (product['discount'] > recommended_product['discount']) or (product['discount'] == recommended_product['discount'] and product['new_price'] < recommended_product['new_price']):
                    recommended_product = product
            except ValueError:
                invalid_products.append(product_data)
        else:
            invalid_products.append(product_data)
    
    # Ensure at least one product is recommended
    if recommended_product is None and selected_products:
        recommended_product = min(selected_products, key=lambda x: x['new_price'])
    
    # Create the plots
    price_plot = px.bar(
        x=product_names, 
        y=unit_prices,  # Use unit prices here
        labels={'x': 'Product', 'y': 'Price per Unit (₹)'},
        title="Price per Unit of Selected Products (₹)",
        color=product_names,  # Add color for better visualization
        text=unit_prices  # Display unit prices on bars
    )
    price_plot.update_traces(texttemplate='₹%{text:.2f}', textposition='outside')

    discount_plot = px.bar(
        x=product_names, 
        y=discounts, 
        labels={'x': 'Product', 'y': 'Discount (%)'},
        title="Discounts on Selected Products",
        color=product_names,  # Add color for better visualization
        text=discounts  # Display discounts on bars
    )
    discount_plot.update_traces(texttemplate='%{text}%', textposition='outside')

    stock_plot = go.Figure(
        data=[go.Pie(
            labels=["In Stock", "Out of Stock"],
            values=[in_stock_counts["In Stock"], in_stock_counts["Out of Stock"]],
            hole=0.3,
            marker=dict(colors=['#4CAF50', '#FF5252'])  # Color the slices
        )],
        layout=go.Layout(title="Stock Availability")
    )

    # Convert the plots to HTML
    price_plot_html = price_plot.to_html(full_html=False)
    discount_plot_html = discount_plot.to_html(full_html=False)
    stock_plot_html = stock_plot.to_html(full_html=False)

    # Render the dashboard with plots and product data
    return render_template(
    "dashboard.html",
    selected_products=selected_products,
    recommended_products=[recommended_product] if recommended_product else [],  # Convert to a list
    price_plot_html=price_plot_html,
    discount_plot_html=discount_plot_html,
    stock_plot_html=stock_plot_html
)

def get_product_by_id(product_id, data_paths):
    """Fetch product details from JSON files by product ID."""
    for platform, path in data_paths.items():
        try:
            with open(path, 'r', encoding='utf-8') as file:
                products = json.load(file)
                for product in products:
                    if str(product.get('id')) == str(product_id):
                        product['platform'] = platform.capitalize()
                        return product
        except Exception as e:
            print(f"Error reading {platform} data: {e}")
    return None

if __name__ == "__main__":
    app.run(debug=True, port=5000)
