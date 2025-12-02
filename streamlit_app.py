### streamlit_app.py

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ---------- CONFIG ----------
DB_URL = "postgresql://rp_mini_project2_db_user:U19DegnNWLaUCDSx03KNO4TB6JQYDefE@dpg-d4ni44qdbo4c73fieseg-a.ohio-postgres.render.com/rp_mini_project2_db"
APP_PASSWORD = "preo123"  

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Mini Project 2 Demo", layout="wide")
st.title("Mini Project 2 – Render + PostgreSQL Demo")

# ---------- PASSWORD GATE ----------
password = st.text_input("Enter app password", type="password")

if password != APP_PASSWORD:
    st.warning("Enter the correct password to continue.")
    st.stop()

st.success("Logged in successfully!!")

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("About this app")
    st.write("""
        This Streamlit application was created for **Mini Project 2**.  
        It demonstrates how to:

        - Deploy a **PostgreSQL database on Render**
        - Connect to that database from **Streamlit using SQLAlchemy**
        - Run **sample JOIN queries** against the normalized MP2 schema
        - Allow users to run **custom SQL queries** through the app
        - Protect the app using a simple **password login**

        The database contains the following normalized tables:

        - Region  
        - Country  
        - Customer  
        - ProductCategory  
        - Product  
        - OrderDetail  

        Use the left panel to run a sample query, or the right panel to test your own SQL.
        """)


    if st.button("Run sample query"):
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

with right_col:
    st.subheader("Run a custom SQL query")

    default_query = """
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
    LIMIT 10;
    """

    user_query = st.text_area("Write a SQL query:", value=default_query, height=200)

    if st.button("Execute custom query"):
        try:
            engine = create_engine(DB_URL)
            with engine.connect() as conn:
                df = pd.read_sql(text(user_query), conn)
            st.write("Query results:")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error running your query: {e}")
