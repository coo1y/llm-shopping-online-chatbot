import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

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

except Exception as error:
    print(f"Error connecting to the database: {error}")
    raise error

def get_db_url():
    return f"postgresql://{DBUSER}:{DBPASS}@{DBHOST}:5432/{DBNAME}"
    
def add_product_cart(product_id, user_id=1):
    cur.execute("""
            SELECT quantity 
            FROM shopping_cart 
            WHERE user_id = %s AND product_id = %s AND shopping_cart.status = 'CART'
        """, (user_id, product_id))
    
    result = cur.fetchone()

    ## If the product exists, update the quantity
    if result:
        new_quantity = result[0] + 1
        cur.execute("""
            UPDATE shopping_cart 
            SET quantity = %s 
            WHERE user_id = %s AND product_id = %s AND shopping_cart.status = 'CART'
            """, (new_quantity, user_id, product_id))

    ## If the product doesn't exist, insert a new row
    else:
        cur.execute("""
            INSERT INTO shopping_cart (user_id, product_id, quantity, status) 
            VALUES (%s, %s, %s, 'CART')
        """, (user_id, product_id, 1))

def buy_product_cart(user_id=1):
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

