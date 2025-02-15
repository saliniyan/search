import React, { useState, useEffect } from "react";

const App = () => {
  const [productName, setProductName] = useState("");
  const [message, setMessage] = useState("");
  const [products, setProducts] = useState(null);

  const handleScrape = async () => {
    if (!productName) {
      setMessage("Please enter a product name.");
      return;
    }

    setMessage("Scraping in progress...");

    try {
      const response = await fetch("http://127.0.0.1:5000/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_name: productName }),
      });

      const data = await response.json();
      if (response.ok) {
        setMessage(data.message);
        setTimeout(fetchProducts, 5000); // Delay to allow scraping completion
      } else {
        setMessage(`Error: ${data.error}`);
      }
    } catch (error) {
      setMessage("Failed to connect to the server.");
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await fetch("http://127.0.0.1:5000/products");
      const data = await response.json();
      setProducts(data);
    } catch (error) {
      console.error("Error fetching products:", error);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>Product Scraper</h1>
      <input
        type="text"
        placeholder="Enter product name"
        value={productName}
        onChange={(e) => setProductName(e.target.value)}
        style={{ padding: "10px", fontSize: "16px", width: "250px" }}
      />
      <button
        onClick={handleScrape}
        style={{
          marginLeft: "10px",
          padding: "10px 20px",
          fontSize: "16px",
          cursor: "pointer",
        }}
      >
        Scrape
      </button>
      <p style={{ marginTop: "20px", fontSize: "18px" }}>{message}</p>

      {products && (
        <div style={{ marginTop: "30px" }}>
          <h2>Scraped Products</h2>
          {Object.keys(products).map((platform) => (
            <div key={platform} style={{ marginBottom: "20px" }}>
              <h3>{platform.toUpperCase()}</h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "20px", justifyContent: "center" }}>
                {products[platform]?.length > 0 ? (
                  products[platform].map((product, index) => (
                    <div key={index} style={{ border: "1px solid #ddd", padding: "10px", width: "200px" }}>
                      <img src={product.image_url} alt={product.name} style={{ width: "100%", height: "150px" }} />
                      <p><strong>{product.name}</strong></p>
                      <p>₹{product.new_price}</p>
                      {product.old_price && <p style={{ textDecoration: "line-through" }}>₹{product.old_price}</p>}
                      <a href={product.product_url} target="_blank" rel="noopener noreferrer">View</a>
                    </div>
                  ))
                ) : (
                  <p>No products found</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default App;
