# LLM Chatbot for Online Shopping

A Python-based chatbot application using a large language model (LLM) to enhance online shopping experiences. The chatbot is built with **Streamlit** for the user interface, **OpenAI** for natural language processing, and **PostgreSQL** as the database for storing product information and shopping cart.

## Features

- Interactive chatbot for online shopping assistance.
- Natural language understanding powered by OpenAI's API.
- Product recommendations and personalized shopping suggestions.
- Persistent data storage using PostgreSQL.
- Web-based interface built with Streamlit.

## Tech Stack

- **Python**: Core programming language.
- **Streamlit**: Web framework for building interactive web apps.
- **OpenAI API**: For leveraging the power of large language models (LLM) and retrieval augmented generation (RAG).
- **PostgreSQL**: Relational database for storing product and user information.

## Installation

1. **Clone the repository**:
```
git clone https://github.com/your-username/llm-shopping-online-chatbot.git
cd llm-shopping-online-chatbot
```

2. **Set up a virtual environment (optional but recommended)**:
```
python3 -m venv env
source env/bin/activate
```

3. **Install the required dependencies**:
```
pip install -r requirements.txt
```

4. **Set up environment variables**:
- Create a .env file in the root directory of the project and add the following variables:
```.env
# OPENAI
OPENAI_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
OPENAI_EMBED=text-embedding-3-small

# POSTGRES
DBUSER=your_postgresql_user
DBPASS=your_postgresql_password
DBHOST=your_postgresql_host
DBNAME=your_postgresql_database
```

5. **Set up the PostgreSQL database**:
- Ensure PostgreSQL is installed and running on your machine.
- Ensure pgvector is installed after PostgreSQL (https://github.com/pgvector/pgvector)
- The schemas and data are located in the database/ folder. You can run the SQL scripts to create the schemas and populate the data in the database.

## Usage
1. **Run the Streamlit app**:
```
streamlit run app.py
```

2. You should see the url (such as, `http://localhost:8501`) on the terminal. After accessing that link, you should see the chatbot interface where users can ask shopping-related questions and receive real-time responses from the LLM chatbot.

## Demo
[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/G5F04WKVtmI/0.jpg)](https://www.youtube.com/watch?v=G5F04WKVtmI)
