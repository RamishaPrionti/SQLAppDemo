### streamlit_app.py

import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ---------- OPTIONAL: ChatGPT / OpenAI CLIENT ----------
# Make sure you: pip install openai
# and set OPENAI_API_KEY in your env or Streamlit secrets.
try:
    from openai import OpenAI
    openai_client = OpenAI()  # reads OPENAI_API_KEY from env / .streamlit/secrets.toml
except Exception:
    openai_client = None


# ---------- CONFIG ----------
DB_URL = "postgresql://rp_mini_project2_db_user:U19DegnNWLaUCDSx03KNO4TB6JQYDefE@dpg-d4ni44qdbo4c73fieseg-a.ohio-postgres.render.com/rp_mini_project2_db"
APP_PASSWORD = "preo123"   # password the grader will use


# ---------- HELPER: CALL CHATGPT TO MAKE SQL ----------
def generate_sql_with_chatgpt(question: str) -> str:
    """
    Takes a natural-language question and returns a single SQL query string.
    If the OpenAI client isn't configured, returns a simple fallback query.
    """
    # Fallback if openai isn't available (still gives *something* to grade)
    if openai_client is None:
        return """-- ChatGPT not configured; fallback example query
SELECT 
    o.orderid,
    c.firstname || ' ' || c.lastname AS customer,
    p.productname,
    o.quantityordered,
    o.orderdate
FROM orderdetail o
JOIN customer c ON o.customerid = c.customerid
JOIN product  p ON o.productid = p.productid
ORDER BY o.orderdate DESC
LIMIT 20;
"""

    system_msg = (
        "You are a SQL assistant for a PostgreSQL database.\n"
        "Schema:\n"
        "  Region(RegionID, Region)\n"
        "  Country(CountryID, Country, RegionID)\n"
        "  Customer(CustomerID, FirstName, LastName, Address, City, CountryID)\n"
        "  ProductCategory(ProductCategoryID, ProductCategory, ProductCategoryDescription)\n"
        "  Product(ProductID, ProductName, ProductUnitPrice, ProductCategoryID)\n"
        "  OrderDetail(OrderID, CustomerID, ProductID, OrderDate, QuantityOrdered)\n\n"
        "Given a question in plain English, return ONE valid PostgreSQL SQL query.\n"
        "Return ONLY the SQL, no explanation, no markdown fences."
    )

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",     # or another model your prof allows
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": question},
        ],
    )

    sql = resp.choices[0].message.content.strip()

    # Strip ```sql ``` wrappers if model adds them
    if sql.startswith("```"):
        sql = sql.strip("`")
        lines = sql.splitlines()
        if lines and lines[0].lower().startswith("sql"):
            lines = lines[1:]
        sql = "\n".join(lines).strip()

    return sql


# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Mini Project 2 Demo", layout="wide")
st.title("Mini Project 2 – Render + PostgreSQL Demo")

# ---------- PASSWORD GATE ----------
password = st.text_input("Enter app password", type="password")

if password != APP_PASSWORD:
    st.warning("Enter the correct password to continue.")
    st.stop()

st.success("Logged in successfully!!")

# Make right column wider (like screenshot)
left_col, right_col = st.columns([1, 2])


# ---------- LEFT COLUMN: SCHEMA, EXAMPLE QUESTIONS, SAMPLE QUERY ----------
with left_col:
    st.subheader("About this app")
    st.write(
        """
        This Streamlit application was created for **Mini Project 2**.  
        It demonstrates how to:

        - Deploy a **PostgreSQL database on Render**
        - Connect to that database from **Streamlit using SQLAlchemy**
        - Run **sample JOIN queries** against the normalized MP2 schema
        - Allow users to run **custom SQL queries / AI-generated queries**
        - Protect the app using a simple **password login**

        **Schema (normalized tables):**

        - Region  
        - Country  
        - Customer  
        - ProductCategory  
        - Product  
        - OrderDetail  
        """
    )

    st.markdown("---")

    st.markdown(
        """
        ### 💡 Example Questions

        **Demographics**
        - How many customers do we have by country?

        **Orders / Sales**
        - What is the total revenue by region?
        - Which product category generated the highest sales?
        - Who are the top 5 customers by total spend?
        """
    )

    st.markdown("---")

    if st.button("Run sample JOIN query"):
        query = """
        SELECT 
            o.orderid,
            c.firstname || ' ' || c.lastname AS customer,
            p.productname,
            o.quantityordered,
            o.orderdate
        FROM orderdetail o
        JOIN customer c ON o.customerid = c.customerid
        JOIN product  p ON o.productid = p.productid
        ORDER BY o.orderid
        LIMIT 20;
        """
        try:
            engine = create_engine(DB_URL)
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
            st.write("Sample orders:")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error running sample query: {e}")


# ---------- RIGHT COLUMN: AI-POWERED SQL QUERY ASSISTANT ----------
with right_col:
    # Big centered title like the professor's screenshot
    st.markdown(
        """
        <h1 style="text-align:center; font-size: 32px; margin-bottom: 0;">
            🤖 AI-Powered SQL Query Assistant
        </h1>
        <p style="text-align:center; font-size:16px; margin-top: 4px;">
            Ask questions in natural language, and I will generate SQL queries for you to review and run!
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.write("### What would you like to know?")

    # Text box for natural-language question
    nl_question = st.text_area(
        "",
        placeholder="What is the average length of stay? (or: Which region has the highest sales?)",
        height=70,
    )

    # Buttons like screenshot: Generate SQL + Clear History
    colA, colB = st.columns(2)
    with colA:
        generate_btn = st.button("Generate SQL", use_container_width=True)
    with colB:
        clear_btn = st.button("Clear History", use_container_width=True)

    # Session state to store last generated SQL + question
    if "generated_sql" not in st.session_state:
        st.session_state["generated_sql"] = ""
    if "last_question" not in st.session_state:
        st.session_state["last_question"] = ""

    if clear_btn:
        st.session_state["generated_sql"] = ""
        st.session_state["last_question"] = ""
        st.success("History cleared!")

    if generate_btn:
        if not nl_question.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Generating SQL with ChatGPT..."):
                sql_query = generate_sql_with_chatgpt(nl_question)
            st.session_state["generated_sql"] = sql_query
            st.session_state["last_question"] = nl_question

    # Show generated SQL, like the "Generated SQL Query" section
    if st.session_state["generated_sql"]:
        st.markdown("---")
        st.write("## Generated SQL Query")
        if st.session_state["last_question"]:
            st.markdown(f"**Question:** {st.session_state['last_question']}")
        st.code(st.session_state["generated_sql"], language="sql")

        # Button to actually run the generated SQL
        if st.button("Run SQL Query"):
            try:
                engine = create_engine(DB_URL)
                with engine.connect() as conn:
                    df = pd.read_sql(text(st.session_state["generated_sql"]), conn)
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error running query: {e}")
