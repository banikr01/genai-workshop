import pandas as pd
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create an OpenAI client using API key and optionally, the base URL
client = OpenAI(
    api_key= os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
)

# Helper function to generate table schema and sample data
def generate_table_info(table, cursor):
    
    result = f"\nSchema for table {table}"
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table})")
    schema = cursor.fetchall()
    
    columns = []
    
    for col in schema:
        columns.append(col[1])
        result += f"\n\t {col[1]} {col[2]}"
    
    result += "\n\n"
    
    # Generate table representation
    cursor.execute(f"SELECT * FROM {table} LIMIT 10")
    data = str(pd.DataFrame(cursor.fetchall(), columns = columns))
    
    result += f"Sample data for table {table} \n"
    result += data + "\n"
    
    return result

# Expects a SQLite database file
DATABASE_NAME = 'movies.sqlite'

# Connect to database and get cursor
conn = sqlite3.connect(DATABASE_NAME)
c = conn.cursor()

# Get list of tables
c.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name;")
tables = c.fetchall()
tables = list(map(lambda x: x[0], tables))

# Generate information on the entire database
database_info = ""

for table in tables:
    database_info += generate_table_info(table, c) + "\n"

question = input("\nAsk me a question: ")

query = f"""{database_info}

As a senior analyst, given the above schemas and data, write a detailed and correct SQLite sql query to answer the analytical question:
    
"{question}"

For your query, only use columns actualy available in the table (refer to schema for the same). 
Also, only apply those filters that are absolutely required.
Return only the query and nothing else. If you respond with nothing but the query, I'll tip you $1000.
    
Output format:
Return your query and nothing else.

Q: Which is the highest grossing movie?
A: 
SELECT original_title
FROM movies
WHERE revenue = (SELECT MAX(revenue) FROM movies);

Q: 


"""

messageHistory = [
    {"role": "user", "content": query}
]

response = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages = messageHistory,
  temperature=0.0,
  max_tokens=500,
)

messageHistory.append(response.choices[0].message)

answer = response.choices[0].message.content

print(f"""

This is the SQL query I ran:
{answer}
""")

c.execute(answer)

output = f"""

This is the response I got:

{c.fetchall()}
"""

print(output)

### Implementing feedback loop

while True:

    feedback = input("\nPress enter if you're satisfied with the response. Else, provide feedback on how to improve my answer:\n")

    if feedback == '':
        break
    else:

        messageHistory.append({"role": "user", "content": feedback + "\nComment only the query and nothing else."})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages = messageHistory,
            temperature=0.0,
            max_tokens=1000,
        )

        messageHistory.append(response.choices[0].message)

        answer = response.choices[0].message.content
        c.execute(answer)

        output = f"""
This is the SQL query I ran:

{answer}

This is the response I got:

{c.fetchall()}
        """

        print(output)


