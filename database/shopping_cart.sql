CREATE TABLE shopping_cart (
    id SERIAL PRIMARY KEY,
    user_id INT,
    product_id INT,
    quantity INT,
  	status TEXT,
  	status_date DATE,
  	estimated_arrival_date DATE
);
