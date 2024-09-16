CREATE TABLE product_listing (
  id serial,
  name TEXT,
  main_category TEXT,
  sub_category TEXT,
  image TEXT,
  link TEXT,
  ratings FLOAT,
  no_of_ratings TEXT,
  discount_price_dollar FLOAT,
  actual_price_dollar FLOAT,
  description TEXT,
  embedded_description VECTOR,
  PRIMARY KEY (id)
);

COPY product_listing(name,main_category,sub_category,image,link,ratings,no_of_ratings,discount_price_dollar,actual_price_dollar,description,embedded_description)
FROM '/path/to/database/product_listing.csv'
DELIMITER ','
CSV HEADER;
