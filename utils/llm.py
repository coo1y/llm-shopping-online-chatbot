import os
import json
import openai
from utils import db_llm
from dotenv import load_dotenv
load_dotenv(override=True)

MODEL_NAME = os.getenv("OPENAI_MODEL")
client = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))
system_message = [
    {"role": "system", "content": "The user's id is 1. You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. You are responsible to answer questions from the users. If the user don't know what to buy, just ask them for more detail about what the user wants. Try to convince the user to buy something the user need. If question isn't about health, nutrition, exercise, and products in the shop, don't answer the question and said the question isn't related."},
]
custom_functions = [
    {
        "name": "search_products",
        "description": "Search PostgreSQL database for relevant products based on user query",
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Query string to use for full text search, e.g. 'protein powder'",
                },
               "price_filter": {
                    "type": "object",
                    "description": "Filter search results based on price of the product",
                    "properties": {
                        "comparison_operator": {
                            "type": "string",
                            "description": "Operator to compare the column value, either '>', '<', '>=', '<=', '='",  # noqa
                        },
                        "value": {
                            "type": "number",
                            "description": "Value to compare against, e.g. 30",
                        },
                    },
                },
            },
            "required": ["search_query"],
        },
    },
    {
        "name": "show_cart",
        "description": "List a shopping cart in PostgreSQL database based on user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "User identification, e.g. 1",
                }
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "add_product_to_cart",
        "description": "Add products into a shopping cart in PostgreSQL database based on user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "User identification, e.g. 1",
                },
                "search_query": {
                    "type": "string",
                    "description": "Query string to use for full text search, e.g. 'protein powder'",
                },
                "quantity": {
                    "type": "integer",
                    "description": "The number of products added, e.g. 3",
                },
            },
            "required": ["user_id", "search_query"],
        },
    },
    {
        "name": "remove_product_from_cart",
        "description": "Remove products out of a shopping cart in PostgreSQL database based on user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "User identification, e.g. 1",
                },
                "search_query": {
                    "type": "string",
                    "description": "Query string to use for full text search, e.g. 'protein powder'",
                },
            },
            "required": ["user_id", "search_query"],
        },
    },
    {
        "name": "update_product_quantity",
        "description": "Update products' quantity in a shopping cart in PostgreSQL database based on user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "User identification, e.g. 1",
                },
                "search_query": {
                    "type": "string",
                    "description": "Query string to use for full text search, e.g. 'protein powder'",
                },
                "quantity": {
                    "type": "integer",
                    "description": "The number of products expected to update, e.g. 3",
                },
            },
            "required": ["user_id", "search_query", "quantity"],
        },
    },
    {
        "name": "pay_cart",
        "description": "Make a payment for products in a shopping cart in PostgreSQL database",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "User identification, e.g. 1",
                }
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "check_products_status",
        "description": "Check status of products the user choose in PostgreSQL database",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "User identification, e.g. 1",
                }
            },
            "required": ["user_id"],
        },
    },
]

def reply_prompt(messages, prompt):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=system_message + messages,
        functions=custom_functions,
        function_call="auto",  # Automatically call the function if needed
    )

    # Extract the function call details from the response
    response_message = response.choices[0].message
    function_call = response_message.function_call

    if function_call:
        function_name = function_call.name
        function_args = json.loads(function_call.arguments)
        print("function_args: ", function_name, "function_args: ", function_args)
        
        # Check if the function call matches the defined schema
        if function_name == "search_products":
            ## Call the function with arguments
            formatted_results = db_llm.search_products_llm(*list(function_args.values()))

            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. The user wants to know whether products are in the store. Then, convince the user to buy products in the list. Say apology and don't show recommendation if no matched product in sources. You just show the product name with bold format, italic price in dollar behind the name, and description with bullet point."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        elif function_name == "show_cart":
            ## Call the function with arguments
            formatted_results = db_llm.show_cart(*list(function_args.values()))

            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. You just tell the user the products (in the sources) in the shopping cart in table format with total price under the table. The header of the table including only Product, Price, Quantity, and Total. If it is empty, tell that it is empty and convince the user to buy something."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        elif function_name == "add_product_to_cart":
            ## Call the function with arguments
            formatted_results = db_llm.add_product_to_cart(*list(function_args.values()))

            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. The user wants to add products into the shopping cart. If done, means the system add completely, don't want to know product name, and ask the user to buy others. If error, beg the user to try again."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        elif function_name == "remove_product_from_cart":
            ## Call the function with arguments
            formatted_results = db_llm.remove_product_from_cart(*list(function_args.values()))

            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. The user wants to remove products out of the shopping cart. If done, means the system add completely, don't want to know product name, and ask the user to buy others. If error, beg the user to try again."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        elif function_name == "update_product_quantity":
            ## Call the function with arguments
            formatted_results = db_llm.update_product_quantity(*list(function_args.values()))

            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. The user wants to update quantity of a product in the shopping cart. If done, means the system add completely, don't want to know product name, and ask the user to buy others. If error, beg the user to try again."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        elif function_name == "pay_cart":
            ## Call the function with arguments
            formatted_results = db_llm.pay_cart(*list(function_args.values()))
            
            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. The user wants to buy products in the shopping cart. If done, means the payment is complete, will receive all products in a few days, and tell later about this fake payment in bracket. If no products, tell them no products in the cart and convince the user to buy. If error, beg the user to try again."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        elif function_name == "check_products_status":
            ## Call the function with arguments
            formatted_results = db_llm.check_products_status(*list(function_args.values()))

            response_stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a polite clerk of a healthy and nutrition shop named 💪 Healthy & Nutrition Shop 💪. The user wants to check the products current status provided in the source. You just explain the details about the products. The date format is 'ddd d mmm yy'. If no products, tell them no products in the cart and convince the user to buy. If error, beg the user to try again."},
                    {"role": "user", "content": prompt + "\n\nSources:\n\n" + formatted_results}
                ],
                stream=True
            )
            return response_stream, True
        else:
            return "Thank you for your message! I’d love to assist you, but I’m not entirely sure I understand your request. Could you please clarify or provide a bit more detail about what you're looking for?", False
    else:

        return response_message.content, False
