import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

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
# SESSION STATE
# -------------------------------

if "name" not in st.session_state:
    st.session_state.name = None

if "month" not in st.session_state:
    st.session_state.month = datetime.now().strftime("%Y-%m")

# -------------------------------
# SIDEBAR NAVIGATION
# -------------------------------

st.sidebar.title("💼 Expense Tracker")

page = st.sidebar.radio("Navigation", ["Setup Budget", "Dashboard", "Add Expense"])

# Month Switch
selected_month = st.sidebar.text_input("📅 Select Month (YYYY-MM)", st.session_state.month)
st.session_state.month = selected_month

# -------------------------------
# SETUP BUDGET
# -------------------------------

if page == "Setup Budget":

    st.title("💰 Setup Monthly Budget")

    name = st.text_input("Enter your name")
    budget = st.number_input("Monthly Budget", min_value=0.0)

    if st.button("Save Budget"):

        if name and budget > 0:
            st.session_state.name = name

            conn = get_db_connection()
            conn.execute("""
                INSERT OR REPLACE INTO profile (name, month, monthly_budget)
                VALUES (?, ?, ?)
            """, (name, st.session_state.month, budget))

            conn.commit()
            conn.close()

            st.success("✅ Budget saved!")

        else:
            st.warning("⚠ Enter valid details")

# -------------------------------
# DASHBOARD
# -------------------------------

elif page == "Dashboard":

    if not st.session_state.name:
        st.warning("⚠ Please setup budget first")
        st.stop()

    st.title("📊 Dashboard")

    conn = get_db_connection()

    profile = conn.execute(
        "SELECT * FROM profile WHERE name=? AND month=?",
        (st.session_state.name, st.session_state.month)
    ).fetchone()

    expenses = conn.execute(
        "SELECT * FROM expenses WHERE name=? AND date LIKE ? ORDER BY date DESC",
        (st.session_state.name, f"{st.session_state.month}%")
    ).fetchall()

    category_totals = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE name=? AND date LIKE ?
        GROUP BY category
    """, (st.session_state.name, f"{st.session_state.month}%")).fetchall()

    conn.close()

    # FIXED DATAFRAME ✅
    if expenses:
        df = pd.DataFrame([dict(row) for row in expenses])
    else:
        df = pd.DataFrame(columns=["id", "name", "date", "category", "amount"])

    # Calculations
    total_spent = sum(row["total"] for row in category_totals) if category_totals else 0
    budget_val = profile["monthly_budget"] if profile else 0
    remaining = budget_val - total_spent

    # Status
    if budget_val == 0:
        status = "No Budget"
    elif total_spent <= budget_val:
        status = "Within Budget ✅"
    else:
        status = "Over Budget ❌"

    # UI CARDS
    col1, col2, col3 = st.columns(3)

    col1.metric("💵 Budget", f"₹{budget_val}")
    col2.metric("💸 Spent", f"₹{total_spent}")
    col3.metric("💰 Remaining", f"₹{remaining}")

    st.info(f"📌 Status: {status}")

    # TABLE
    if not df.empty:
        st.subheader("📋 Expenses")
        st.dataframe(df)

    else:
        st.warning("No expenses yet")

    # BAR CHART
    if category_totals:
        chart_df = pd.DataFrame([dict(row) for row in category_totals])

        st.subheader("📊 Category Wise Spending")
        st.bar_chart(chart_df.set_index("category"))

        # PIE CHART ✅
        st.subheader("🥧 Expense Distribution")

        fig, ax = plt.subplots()
        ax.pie(chart_df["total"], labels=chart_df["category"], autopct='%1.1f%%')
        ax.axis("equal")

        st.pyplot(fig)

# -------------------------------
# ADD EXPENSE
# -------------------------------

elif page == "Add Expense":

    if not st.session_state.name:
        st.warning("⚠ Setup budget first")
        st.stop()

    st.title("➕ Add Expense")

    date = st.date_input("Date")
    category = st.text_input("Category")
    amount = st.number_input("Amount", min_value=0.0)

    if st.button("Add"):

        if category and amount > 0:

            conn = get_db_connection()
            conn.execute(
                "INSERT INTO expenses (name, date, category, amount) VALUES (?, ?, ?, ?)",
                (st.session_state.name, str(date), category, amount)
            )
            conn.commit()
            conn.close()

            st.success("✅ Expense added")

        else:
            st.warning("⚠ Enter valid data")

# -------------------------------
# DOWNLOAD
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
        st.sidebar.warning("No data")

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
