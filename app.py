import streamlit as st
from streamlit_modal import Modal
import time
from utils import image
from utils import db
from utils import llm

# Layout with shopping page and chat sidebar
st.set_page_config(page_title="💪 Healthy & Nutrition Shop 💪")
st.markdown("<h1 style='text-align: center; color: black;'>🔛🔝 Top Products This Month</h1>", unsafe_allow_html=True)

click_button = {i: None for i in range(1, 7)}

# Create columns for shopping items
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    new_image = image.resize_image("image_product/1_61kakn7F+rL._AC_UL320_.jpg")
    st.image(new_image, caption="""MuscleBlaze Beginner's Whey Protein (Chocolate 1 kg) - $16.19""")

    col11, col12, col13 = st.columns(3)
    with col12:
        click_button[1] = st.button("Add", key=1)

with col2:
    new_image = image.resize_image("image_product/2_81hcIJfQLTL._AC_UL320_.jpg")
    st.image(new_image, caption="""Endura Mass Weight Gainer - 500 g (Chocolate) - $6.76""")
    
    col21, col22, col23 = st.columns(3)
    with col22:
        click_button[2] = st.button("Add", key=2)

with col3:
    new_image = image.resize_image("image_product/3_713Cwx85MbL._AC_UL320_.jpg")
    st.image(new_image, caption="""Neuherbs Skin Collagen, 210g | Collagen Supplement - $8.99""")
    
    col31, col32, col33 = st.columns(3)
    with col32:
        click_button[3] = st.button("Add", key=3)

# Create columns for shopping items
col4, col5, col6 = st.columns(3, gap="large")

with col4:
    new_image = image.resize_image("image_product/4_71fjiF6Q3yL._AC_UL320_.jpg")
    st.image(new_image, caption="""Carbamide Forte Melatonin Gummies 10mg - $5.99""")
    
    col41, col42, col43 = st.columns(3)
    with col42:
        click_button[4] = st.button("Add", key=4)

with col5:
    new_image = image.resize_image("image_product/5_718gTJfVzuL._AC_UL320_.jpg")
    st.image(new_image, caption="""Carbamide Forte Multivitamin (100 Veg Tablets) - $5.99""")
    
    col51, col52, col53 = st.columns(3)
    with col52:
        click_button[5] = st.button("Add", key=5)

with col6:
    new_image = image.resize_image("image_product/6_51BuPqiRAWS._AC_UL320_.jpg")
    st.image(new_image, caption="""Follihair New Nutraceutical Pack of 30N Tablet... - $6.80""")
    
    col61, col62, col63 = st.columns(3)
    with col62:
        click_button[6] = st.button("Add", key=6)

for k in range(1, 7):
    if click_button[k]:
        db.add_product_cart(product_id=k)

st.markdown("<h4 style='text-align: center; color: black;'>💬 Chat with AI Clerk 🤖</h4>", unsafe_allow_html=True)

## Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

## Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

## Accept user input
if prompt := st.chat_input("Message AI Clerk 🤖"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner('Our clerk is thinking...'):
            response, is_stream = llm.reply_prompt(
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                prompt=prompt,
                )
            
            if is_stream:
                content = st.write_stream(response)
            else:
                st.write(response)
                content = response
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": content})

## Cart at sidebar
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: black;'>🛒 Shopping Cart 🛒</h2>", unsafe_allow_html=True)
    db_url = db.get_db_url()
    conn = st.connection("postgresql", type="sql", url=db_url)
    cart_1 = conn.query(""" 
                            SELECT 
                                SUBSTRING(p.name, 1, 40) AS "Product", 
                                p.discount_price_dollar AS "Price per Qty", 
                                sc.quantity AS "Qty", 
                            (p.discount_price_dollar * sc.quantity) AS "Price"
                            FROM shopping_cart sc
                            JOIN product_listing p ON sc.product_id = p.id
                            WHERE sc.user_id = 1 AND sc.status = 'CART'
                        """)

    if len(cart_1) > 0:
        st.dataframe(cart_1, hide_index=True)
        st.write(f"<h5 style='text-align: left; color: black;'>Total Price: ${cart_1["Price"].sum().round(2)}</h5>", unsafe_allow_html=True)

        buy = st.button("Buy Now")
        buy_popup = Modal("Success", key="popup", max_width=400)

        if buy:
            with st.spinner('Please wait...'):
                db.buy_product_cart()
                time.sleep(3)

            buy_popup.open()
        
        if buy_popup.is_open():
            with buy_popup.container():
                st.write("We are delight to inform you that the (fake) transaction is complete.")
                ok = st.button("OK")

                if ok:
                    buy_popup.close()
                    st.cache_data.clear()
                    st.rerun()


    else:
        st.write("<i><p style='text-align: center; color: gray;'>No product in the cart.</p></i>", unsafe_allow_html=True)

# clear data cache
st.cache_data.clear()
