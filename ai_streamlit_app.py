import os
import re

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from openai import OpenAI

# ---------------- CONFIG ----------------

# Your Render DB URL (same as before)
DB_URL = (
    "postgresql://rp_mini_project2_db_user:"
    "U19DegnNWLaUCDSx03KNO4TB6JQYDefE"
    "@dpg-d4ni44qdbo4c73fieseg-a.ohio-postgres.render.com/"
    "rp_mini_project2_db"
)

APP_PASSWORD = "preo123"        # password grader will use

# Try to get API key from env, then from st.secrets
def _get_api_key():
    key = os.environ.get("OPENAI_API_KEY", None)
    if not key:
        key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    return key

OPENAI_API_KEY = _get_api_key()

# Database schema for ChatGPT context – YOUR MP2 SCHEMA
DATABASE_SCHEMA = """
Database Schema (Mini Project 2):

Tables:
- Region(
    RegionID INTEGER PRIMARY KEY,
    Region   TEXT NOT NULL
  )

- Country(
    CountryID INTEGER PRIMARY KEY,
    Country   TEXT NOT NULL,
    RegionID  INTEGER NOT NULL REFERENCES Region(RegionID)
  )

- Customer(
    CustomerID INTEGER PRIMARY KEY,
    FirstName  TEXT NOT NULL,
    LastName   TEXT NOT NULL,
    Address    TEXT NOT NULL,
    City       TEXT NOT NULL,
    CountryID  INTEGER NOT NULL REFERENCES Country(CountryID)
  )

- ProductCategory(
    ProductCategoryID          INTEGER PRIMARY KEY,
    ProductCategory            TEXT NOT NULL,
    ProductCategoryDescription TEXT NOT NULL
  )

- Product(
    ProductID         INTEGER PRIMARY KEY,
    ProductName       TEXT NOT NULL,
    ProductUnitPrice  REAL    NOT NULL,
    ProductCategoryID INTEGER NOT NULL REFERENCES ProductCategory(ProductCategoryID)
  )

- OrderDetail(
    OrderID         INTEGER PRIMARY KEY,
    CustomerID      INTEGER NOT NULL REFERENCES Customer(CustomerID),
    ProductID       INTEGER NOT NULL REFERENCES Product(ProductID),
    OrderDate       DATE    NOT NULL,
    QuantityOrdered INTEGER NOT NULL
  )

Notes:
- To get full customer name, use: FirstName || ' ' || LastName
- To compute total sale for a row: ProductUnitPrice * QuantityOrdered
- Typical questions involve totals by customer, country, or region,
  as well as counts of orders or products.
"""

# ---------------- LOGIN ----------------

def login_screen():
    """Display login screen and authenticate user."""
    st.title("🔐 Secure Login")
    st.markdown("---")
    st.write("Enter your password to access the AI SQL Query Assistant.")

    password = st.text_input("Password", type="password", key="login_password")

    col1, col2, _ = st.columns([1, 1, 3])
    with col1:
        login_btn = st.button("🔓 Login", use_container_width=True)

    if login_btn:
        if not password:
            st.warning("⚠️ Please enter a password")
        elif password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.success("✅ Authentication successful! Redirecting...")
            st.experimental_rerun()
        else:
            st.error("❌ Incorrect password")

    st.markdown("---")
    st.info(
        "This demo uses a simple password check stored in the app code. "
        "In a real system you would store hashed passwords and secrets securely."
    )


def require_login():
    """Enforce login before showing main app."""
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_screen()
        st.stop()


# ---------------- DB & OPENAI HELPERS ----------------

@st.cache_resource
def get_engine():
    """Create and cache SQLAlchemy engine."""
    return create_engine(DB_URL)


def run_query(sql: str):
    """Execute SQL query and return results as DataFrame."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df
    except Exception as e:
        st.error(f"Error executing query:\n\n{e}")
        return None


@st.cache_resource
def get_openai_client():
    """Create and cache OpenAI client."""
    if not OPENAI_API_KEY:
        st.error(
            "OPENAI_API_KEY is not set. "
            "Set it as an environment variable or in Streamlit secrets."
        )
        st.stop()
    return OpenAI(api_key=OPENAI_API_KEY)


def extract_sql_from_response(response_text: str) -> str:
    """
    Remove ```sql ... ``` fences if the model returns them.
    """
    clean_sql = re.sub(
        r"^```sql\s*|\s*```$",
        "",
        response_text,
        flags=re.IGNORECASE | re.MULTILINE,
    ).strip()
    return clean_sql


def generate_sql_with_gpt(user_question: str) -> str | None:
    """Call ChatGPT to generate a SQL query from natural language."""
    client = get_openai_client()

    prompt = f"""
You are a PostgreSQL expert. Given the following database schema and a user's question, 
generate a valid PostgreSQL SQL query.

{DATABASE_SCHEMA}

User Question: {user_question}

Requirements:
1. Return ONLY the SQL query that I can run directly (no explanation, no comments).
2. Use correct table and column names from the schema.
3. Use JOINs where needed (e.g., Customer with Country / Region, Product with Category).
4. When the result might be large, include a LIMIT (default LIMIT 100).
5. Give helpful column aliases using AS.
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You generate accurate PostgreSQL queries for the Mini Project 2 sales database.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        raw = completion.choices[0].message.content
        sql_query = extract_sql_from_response(raw)
        return sql_query
    except Exception as e:
        st.error(f"Error calling OpenAI API:\n\n{e}")
        return None


# ---------------- MAIN APP ----------------

def main():
    require_login()

    st.set_page_config(page_title="MP2 – AI SQL Assistant", layout="wide")

    st.title("🤖 AI-Powered SQL Query Assistant")
    st.markdown(
        "Ask questions in natural language, and the app will generate SQL "
        "for your **Mini Project 2** database."
    )
    st.markdown("---")

    # ---------- Sidebar ----------
    st.sidebar.title("💡 Example Questions")
    st.sidebar.markdown(
        """
Try asking questions like:

**Customers & Orders**
- Which customers have placed the most orders?
- What are the top 5 customers by total spending?

**Regions & Countries**
- What is total sales by region?
- Which country has the highest total sales?

**Products**
- What are the best-selling products?
- Show total quantity ordered by product category.
"""
    )
    st.sidebar.markdown("---")
    st.sidebar.info(
        """
**How it works:**
1. Enter your question in plain English  
2. AI generates a SQL query  
3. Review / edit the SQL  
4. Click **Run Query** to execute it
"""
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    # ---------- Session state ----------
    if "query_history" not in st.session_state:
        st.session_state.query_history = []  # list of dicts: {question, sql, rows}
    if "generated_sql" not in st.session_state:
        st.session_state.generated_sql = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    # ---------- Input: natural language question ----------
    user_question = st.text_area(
        "What would you like to know?",
        height=100,
        placeholder="Example: What are the top 5 customers by total spending?",
    )

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        generate_button = st.button("Generate SQL", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("Clear History", use_container_width=True)

    if clear_button:
        st.session_state.query_history = []
        st.session_state.generated_sql = None
        st.session_state.current_question = None

    if generate_button and user_question.strip():
        uq = user_question.strip()

        # If new question, clear previous SQL
        if st.session_state.current_question != uq:
            st.session_state.generated_sql = None
            st.session_state.current_question = None

        with st.spinner("🧠 ChatGPT is generating a SQL query..."):
            sql_query = generate_sql_with_gpt(uq)
            if sql_query:
                st.session_state.generated_sql = sql_query
                st.session_state.current_question = uq

    # ---------- Show / edit generated SQL ----------
    if st.session_state.generated_sql:
        st.markdown("---")
        st.subheader("Generated SQL Query")
        st.info(f"**Question:** {st.session_state.current_question}")

        edited_sql = st.text_area(
            "Review and edit the SQL query if needed:",
            value=st.session_state.generated_sql,
            height=220,
        )

        run_col, _ = st.columns([1, 5])
        with run_col:
            run_button = st.button("Run Query", type="primary", use_container_width=True)

        if run_button and edited_sql.strip():
            with st.spinner("Executing query..."):
                df = run_query(edited_sql)
                if df is not None:
                    st.session_state.query_history.append(
                        {
                            "question": st.session_state.current_question,
                            "sql": edited_sql,
                            "rows": len(df),
                        }
                    )
                    st.markdown("---")
                    st.subheader("📊 Query Results")
                    st.success(f"✅ Query returned {len(df)} rows")
                    st.dataframe(df, use_container_width=True)

    # ---------- Query history ----------
    if st.session_state.query_history:
        st.markdown("---")
        st.subheader("📜 Query History (last 5)")

        for idx, item in enumerate(reversed(st.session_state.query_history[-5:])):
            label = f"Query {len(st.session_state.query_history) - idx}: {item['question'][:60]}..."
            with st.expander(label):
                st.markdown(f"**Question:** {item['question']}")
                st.code(item["sql"], language="sql")
                st.caption(f"Returned {item['rows']} rows")

                if st.button("Re-run this query", key=f"rerun_{idx}"):
                    df = run_query(item["sql"])
                    if df is not None:
                        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
