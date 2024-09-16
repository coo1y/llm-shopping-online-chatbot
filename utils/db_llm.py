import os
import openai
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv(override=True)

client = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))

## Set up Postgres
DBUSER = os.environ["DBUSER"]
DBPASS = os.environ["DBPASS"]
DBHOST = os.environ["DBHOST"]
DBNAME = os.environ["DBNAME"]
## Use SSL if not connecting to localhost
DBSSL = "disable"
if DBHOST != "localhost":
    DBSSL = "require"

# Function to connect to the database
try:
    conn = psycopg2.connect(database=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, sslmode=DBSSL)
    conn.autocommit = True
    cur = conn.cursor()
    register_vector(conn)
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

except Exception as error:
    print(f"Error connecting to the database: {error}")
    raise error

def search_products_llm(search_query: str, price_filter: dict = None):
    response = client.embeddings.create(input=search_query, model=os.getenv("OPENAI_EMBED"), dimensions=1536)
    embedding = np.array(response.data[0].embedding)

    where_price_filter = "WHERE 1=1"
    if price_filter:
        where_price_filter += f"AND discount_price_dollar {price_filter['comparison_operator']} {price_filter['value']}" 

    SQL_search = f"""
    WITH semantic_search AS (
        SELECT id, RANK() OVER (ORDER BY embedded_description <=> %(embedding)s) AS rank
        FROM product_listing
        {where_price_filter}
        ORDER BY embedded_description <=> %(embedding)s
        LIMIT 20
    ),
    keyword_search AS (
        SELECT id, RANK() OVER (ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC)
        FROM product_listing, plainto_tsquery('english', %(query)s) query
        {where_price_filter} AND to_tsvector('english', description) @@ query
        ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC
        LIMIT 20
    )
    SELECT
        COALESCE(semantic_search.id, keyword_search.id) AS id,
        COALESCE(1.0 / (%(k)s + semantic_search.rank), 0.0) +
        COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS score
    FROM semantic_search
    FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
    ORDER BY score DESC
    LIMIT 5
    """

    cur.execute(SQL_search, {"query": search_query, "embedding": embedding, "k": 60})
    results = cur.fetchall()

    ## Fetch the videos by ID
    ids = [result[0] for result in results]
    cur.execute("""
                SELECT id, name, discount_price_dollar, description, link
                FROM product_listing 
                WHERE id = ANY(%s)"""
                , (ids,))
    results = cur.fetchall()

    ## Format the results for the LLM
    if not results:
        return "No matched products"
    
    formatted_results = ""
    for result in results:
        formatted_results += f"## {result[1]}\n\nprice: ${result[2]}\n\ndescription: {result[3]}\n\nURL: {result[4]}"
    
    return formatted_results

# 0. show a user's cart
def show_cart(user_id=1):
    # Query to get product details and quantity from the shopping cart
    cur.execute("""
        SELECT SUBSTRING(p.name, 1, 50) AS name, p.discount_price_dollar, sc.quantity, (p.discount_price_dollar * sc.quantity) AS total_price
        FROM shopping_cart sc
        JOIN product_listing p ON sc.product_id = p.id
        WHERE sc.user_id = %s AND sc.status = 'CART'
    """, (user_id,))
    
    cart_items = cur.fetchall()

    if cart_items:
        total_all_prices = 0
        formatted_results = ""
        for item in cart_items:
            product_name, price, quantity, total_price = item
            total_all_prices += total_price
            formatted_results += f"Product: {product_name}, Price: {price}, Quantity: {quantity}, Total: {total_price}\n"
        formatted_results += f"\nTotal Price: {total_all_prices}"

        return formatted_results
    else:
        return "Your shopping cart is empty."
    
# 1. Add product to cart
def add_product_to_cart(user_id, search_query: str, quantity):
    try:
        ## Turn the question into an embedding
        client = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))
        response = client.embeddings.create(input=search_query, model=os.getenv("OPENAI_EMBED"), dimensions=1536)
        embedding = np.array(response.data[0].embedding)

        SQL_search = f"""
        WITH semantic_search AS (
            SELECT id, RANK() OVER (ORDER BY embedded_description <=> %(embedding)s) AS rank
            FROM product_listing
            ORDER BY embedded_description <=> %(embedding)s
            LIMIT 20
        ),
        keyword_search AS (
            SELECT id, RANK() OVER (ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC)
            FROM product_listing, plainto_tsquery('english', %(query)s) query
            WHERE to_tsvector('english', description) @@ query
            ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC
            LIMIT 20
        )
        SELECT
            COALESCE(semantic_search.id, keyword_search.id) AS id,
            COALESCE(1.0 / (%(k)s + semantic_search.rank), 0.0) +
            COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS score
        FROM semantic_search
        FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
        ORDER BY score DESC
        LIMIT 1
        """

        cur.execute(SQL_search, {"query": search_query, "embedding": embedding, "k": 60})
        result = cur.fetchone()
        product_id = result[0]

        # Check if product already exists in the cart
        cur.execute("""
            SELECT quantity 
            FROM shopping_cart 
            WHERE user_id = %s AND product_id = %s AND shopping_cart.status = 'CART'
        """, (user_id, product_id))
        
        result = cur.fetchone()
        
        if result:
            # If the product exists, update the quantity
            new_quantity = result[0] + quantity
            cur.execute("""
                UPDATE shopping_cart 
                SET quantity = %s 
                WHERE user_id = %s AND product_id = %s AND shopping_cart.status = 'CART'
            """, (new_quantity, user_id, product_id))

            return "Done. Already add your product more."
        else:
            # If the product doesn't exist, insert a new row
            cur.execute("""
                INSERT INTO shopping_cart (user_id, product_id, quantity, status) 
                VALUES (%s, %s, %s, 'CART')
            """, (user_id, product_id, quantity))

            return "Done. The product is in the shopping cart."

    except (Exception, psycopg2.DatabaseError) as error:
        return f"Error: {error}"
    
# 2. Remove product from cart
def remove_product_from_cart(user_id, search_query):
    try:
        ## Turn the question into an embedding
        client = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))
        response = client.embeddings.create(input=search_query, model=os.getenv("OPENAI_EMBED"), dimensions=1536)
        embedding = np.array(response.data[0].embedding)

        SQL_search = f"""
        WITH semantic_search AS (
            SELECT id, RANK() OVER (ORDER BY embedded_description <=> %(embedding)s) AS rank
            FROM product_listing
            ORDER BY embedded_description <=> %(embedding)s
            LIMIT 20
        ),
        keyword_search AS (
            SELECT id, RANK() OVER (ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC)
            FROM product_listing, plainto_tsquery('english', %(query)s) query
            WHERE to_tsvector('english', description) @@ query
            ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC
            LIMIT 20
        ),
        search AS (
            SELECT
                COALESCE(semantic_search.id, keyword_search.id) AS id,
                COALESCE(1.0 / (%(k)s + semantic_search.rank), 0.0) +
                COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS score
            FROM semantic_search
            FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
            ORDER BY score DESC
            LIMIT 5
        )

        SELECT shopping_cart.product_id
        FROM shopping_cart
        INNER JOIN search ON shopping_cart.product_id = search.id
        WHERE shopping_cart.user_id = %(user_id)s AND shopping_cart.status = 'CART'
        ORDER BY search.score DESC
        LIMIT 1
        """

        cur.execute(SQL_search, {"query": search_query, "embedding": embedding, "k": 60, "user_id": user_id})
        result = cur.fetchone()

        if result:
            product_id = result[0]
            cur.execute("""
                DELETE 
                FROM shopping_cart 
                WHERE user_id = %s AND product_id = %s AND status = 'CART'
            """, (user_id, product_id))

            return "Done"
        else:
            return "The product isn't in the cart."
    
    except (Exception, psycopg2.DatabaseError) as error:
        return f"Error: {error}"

# 3. Update product quantity in cart
def update_product_quantity(user_id, search_query, quantity=1):
    try:
        # Check if product already exists in the cart
        ## Turn the question into an embedding
        client = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))
        response = client.embeddings.create(input=search_query, model=os.getenv("OPENAI_EMBED"), dimensions=1536)
        embedding = np.array(response.data[0].embedding)

        SQL_search = f"""
        WITH semantic_search AS (
            SELECT id, RANK() OVER (ORDER BY embedded_description <=> %(embedding)s) AS rank
            FROM product_listing
            ORDER BY embedded_description <=> %(embedding)s
            LIMIT 20
        ),
        keyword_search AS (
            SELECT id, RANK() OVER (ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC)
            FROM product_listing, plainto_tsquery('english', %(query)s) query
            WHERE to_tsvector('english', description) @@ query
            ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC
            LIMIT 20
        ),
        search AS (
            SELECT
                COALESCE(semantic_search.id, keyword_search.id) AS id,
                COALESCE(1.0 / (%(k)s + semantic_search.rank), 0.0) +
                COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS score
            FROM semantic_search
            FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
            ORDER BY score DESC
            LIMIT 5
        )

        SELECT shopping_cart.product_id, shopping_cart.quantity
        FROM shopping_cart
        INNER JOIN search ON shopping_cart.product_id = search.id
        WHERE shopping_cart.user_id = %(user_id)s AND shopping_cart.status = 'CART'
        ORDER BY search.score DESC
        LIMIT 1
        """

        cur.execute(SQL_search, {"query": search_query, "embedding": embedding, "k": 60, "user_id": user_id})
        result = cur.fetchone()

        if result[1] == quantity:
            return "Please validate your quantity. They are same."
        elif result:
            product_id = result[0]
            
            cur.execute("""
                UPDATE shopping_cart 
                SET quantity = %s 
                WHERE user_id = %s AND product_id = %s AND status = 'CART'
            """, (quantity, user_id, product_id))

            return "Done"
        else:
            return "The product is not in the cart."

    except (Exception, psycopg2.DatabaseError) as error:
        return f"Error: {error}"
    
def pay_cart(user_id=1):
    """
    This function is to pay for products in the cart. The payment is fake. 
    Just Update that the user already paid for their products
    """
    try:
        # Check if product already exists in the cart
        cur.execute("""
            SELECT product_id 
            FROM shopping_cart 
            WHERE user_id = %s AND quantity > 0 AND status = 'CART'
        """, (user_id, ))

        results = cur.fetchall()
        if results:
            cur.execute("""
                        UPDATE shopping_cart 
                        SET status = 'PAID', status_date = CURRENT_DATE, estimated_arrival_date = CURRENT_DATE + 3
                        WHERE user_id = %s AND status = 'CART'
                    """, (user_id, ))
            
            return "Done"
        else:
            return "There are no products in the shopping cart."
    
    except (Exception, psycopg2.DatabaseError) as error:
        return f"Error: {error}"
    
def check_products_status(user_id=1):
    try:
        # Check if product already exists in the cart
        cur.execute("""
                    SELECT p.name, sc.quantity, sc.status, sc.estimated_arrival_date
                    FROM shopping_cart sc
                    JOIN product_listing p ON sc.product_id = p.id
                    WHERE sc.user_id = %s
                    """, (user_id, ))

        items = cur.fetchall()
        if items:
            formatted_results = ""
            for item in items:
                product_name, quantity, status, est_arrival = item
                formatted_results += f"Product: {product_name}, Quantity: {quantity}, Status: {status}, Estimated Date Arrival: {est_arrival}\n, "
            
            return formatted_results
        else:
            return "There are no products."
    except (Exception, psycopg2.DatabaseError) as error:
        return f"Error: {error}"
