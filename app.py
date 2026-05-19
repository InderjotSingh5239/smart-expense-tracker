import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# -------------------------------
# DATABASE
# -------------------------------

def get_db_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        month TEXT,
        monthly_budget REAL,
        UNIQUE(name, month)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        category TEXT,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------------
# SESSION STATE (replacement of Flask session)
# -------------------------------

if "name" not in st.session_state:
    st.session_state.name = None

if "month" not in st.session_state:
    st.session_state.month = datetime.now().strftime("%Y-%m")

# -------------------------------
# PAGE NAVIGATION
# -------------------------------

page = st.sidebar.selectbox("Navigation", ["Setup Budget", "Dashboard", "Add Expense"])

# -------------------------------
# 1. SETUP BUDGET
# -------------------------------

if page == "Setup Budget":

    st.title("💰 Setup Monthly Budget")

    name = st.text_input("Enter your name")
    month = st.text_input("Month (YYYY-MM)", value=st.session_state.month)
    budget = st.number_input("Monthly Budget", min_value=0.0)

    if st.button("Save Budget"):

        if name and budget > 0:
            st.session_state.name = name
            st.session_state.month = month

            conn = get_db_connection()
            conn.execute("""
                INSERT OR REPLACE INTO profile (name, month, monthly_budget)
                VALUES (?, ?, ?)
            """, (name, month, budget))
            conn.commit()
            conn.close()

            st.success("Budget saved successfully!")

        else:
            st.warning("Please enter valid details")

# -------------------------------
# 2. DASHBOARD
# -------------------------------

elif page == "Dashboard":

    if not st.session_state.name:
        st.warning("Please set up your budget first.")
        st.stop()

    st.title("📊 Dashboard")

    month = st.text_input("Select Month", value=st.session_state.month)
    st.session_state.month = month

    conn = get_db_connection()

    profile = conn.execute(
        "SELECT * FROM profile WHERE name=? AND month=?",
        (st.session_state.name, month)
    ).fetchone()

    expenses = conn.execute(
        "SELECT * FROM expenses WHERE name=? AND date LIKE ? ORDER BY date DESC",
        (st.session_state.name, f"{month}%")
    ).fetchall()

    category_totals = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE name=? AND date LIKE ?
        GROUP BY category
        ORDER BY total DESC
    """, (st.session_state.name, f"{month}%")).fetchall()

    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(expenses, columns=["id", "name", "date", "category", "amount"])

    total_spent = sum(row['total'] for row in category_totals) if category_totals else 0
    budget_val = profile['monthly_budget'] if profile else 0
    remaining = budget_val - total_spent if budget_val else 0

    # STATUS
    if budget_val == 0:
        status = "No Budget Set"
    elif total_spent <= budget_val:
        status = "Within Budget"
    else:
        status = "Over Budget"

    # TOP CATEGORY
    highest_category = category_totals[0]['category'] if category_totals else "None"

    # SUGGESTION
    if budget_val == 0:
        suggestion = "Please set a budget first."
    elif total_spent > budget_val:
        suggestion = f"Exceeded by ₹{total_spent - budget_val}. Reduce {highest_category}."
    elif total_spent > (budget_val * 0.8):
        suggestion = "80% budget used. Be careful!"
    else:
        suggestion = "You're doing great!"

    # UI
    st.write(f"### 👤 User: {st.session_state.name}")
    st.write(f"### 💵 Budget: ₹{budget_val}")
    st.write(f"### 💸 Spent: ₹{total_spent}")
    st.write(f"### 💰 Remaining: ₹{remaining}")
    st.write(f"### ⚠ Status: {status}")
    st.info(suggestion)

    if not df.empty:
        st.subheader("📋 Expenses")
        st.dataframe(df)

        # Chart
        chart_df = pd.DataFrame(category_totals, columns=["category", "total"])
        st.subheader("📊 Category Distribution")
        st.bar_chart(chart_df.set_index("category"))

    else:
        st.info("No expenses found")

# -------------------------------
# 3. ADD EXPENSE
# -------------------------------

elif page == "Add Expense":

    if not st.session_state.name:
        st.warning("Please set up your budget first.")
        st.stop()

    st.title("➕ Add Expense")

    date = st.date_input("Select Date")
    category = st.text_input("Category")
    amount = st.number_input("Amount", min_value=0.0)

    if st.button("Add Expense"):

        if category and amount > 0:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO expenses (name, date, category, amount) VALUES (?, ?, ?, ?)",
                (st.session_state.name, str(date), category, amount)
            )
            conn.commit()
            conn.close()

            st.success("Expense added!")

        else:
            st.warning("Enter valid data")

# -------------------------------
# DOWNLOAD CSV
# -------------------------------

st.sidebar.subheader("⬇ Export")

if st.sidebar.button("Download CSV"):
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()

    if not df.empty:
        df.to_csv("expenses.csv", index=False)
        st.sidebar.success("Downloaded!")
    else:
        st.sidebar.warning("No data available")

# -------------------------------
# RESET
# -------------------------------

if st.sidebar.button("Reset Data"):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM profile")
    conn.commit()
    conn.close()
    st.sidebar.success("All data cleared!")
