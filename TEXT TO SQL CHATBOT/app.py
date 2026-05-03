import os
from flask import Flask, render_template, request, jsonify
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.chat_models import ChatOllama
import sqlalchemy
import pymysql

app = Flask(__name__)

# Connect MySQL database
host = 'localhost'
port = '3306'
username = 'root'
password = 'root'
database_schema = 'text_to_sql'

mysql_uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_schema}"

db = None
try:
    db = SQLDatabase.from_uri(mysql_uri, sample_rows_in_table_info=2)
except Exception as e:
    print(f"Warning: Could not connect to database. {e}")

# get the schema of the database
def get_schema(_):
    if db:
        return db.get_table_info()
    return "Schema not available."

template = """Based on the table schema below, write a SQL query that would answer the user's question:
Remember : Only provide me the sql query dont include anything else. Provide me sql query in a single line dont add line breaks
Table Schema: {schema}
Question: {question}
SQL Query:
"""

prompt = ChatPromptTemplate.from_template(template)

llm = ChatOllama(model="tinyllama")

if db:
    sql_chain = (
        RunnablePassthrough.assign(schema=get_schema) 
        | prompt
        | llm.bind(stop=["\nSQLResult:"])
        | StrOutputParser()
    )
else:
    sql_chain = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
        
    if not sql_chain:
         return jsonify({'error': 'System is not fully initialized. Check database connection.'}), 500

    try:
        query = sql_chain.invoke({"question": question})
        # Clean up output
        query = query.strip()
        if query.startswith("```sql"):
            query = query.replace("```sql", "").replace("```", "")
            
        return jsonify({'query': query.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
