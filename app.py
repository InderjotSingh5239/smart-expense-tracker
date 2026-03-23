from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "monthly_expense_secret_2026"


# -------------------------------
# DATABASE CONNECTION
# -------------------------------

def get_db_connection():
    conn = sqlite3.connect("database.db")
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
# HOME / BUDGET SETUP
# -------------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        session['name'] = request.form.get("name")
        session['selected_month'] = request.form.get("month")
        budget = request.form.get("budget")

        conn = get_db_connection()

        conn.execute("""
        INSERT OR REPLACE INTO profile (name, month, monthly_budget)
        VALUES (?, ?, ?)
        """, (session['name'], session['selected_month'], float(budget)))

        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template("budget.html")


# -------------------------------
# DASHBOARD
# -------------------------------

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    # Update month when form is submitted
 if request.method == "POST":
    selected = request.form.get("month")
    if selected:
        session['selected_month'] = selected

#  Set default month only once
if 'selected_month' not in session:
    session['selected_month'] = datetime.now().strftime("%Y-%m")

#  ALWAYS use this (outside if)
target_month = session['selected_month']

print("DEBUG → Month:", target_month)

#  Now database logic
conn = get_db_connection()

profile = conn.execute(
    "SELECT * FROM profile WHERE name=? AND month=?",
    (session['name'], target_month)
).fetchone()

expenses = conn.execute(
    "SELECT * FROM expenses WHERE name=? AND date LIKE ? ORDER BY date DESC",
    (session['name'], f"{target_month}%")
).fetchall()

    category_totals = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE name=? and date LIKE ?
        GROUP BY category
        ORDER BY total DESC
    """, (session['name'], f"{target_month}%",)).fetchall()

    # -------------------------------
    # CALCULATIONS
    # -------------------------------

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
    suggestion = f"You've exceeded your limit by ₹{total_spent - budget_val}. Try reducing {highest_category}."
elif total_spent > (budget_val * 0.8):
    suggestion = "You've used 80% of your budget. Be careful!"
else:
    suggestion = "You're doing great! Your spending is well under control."

# CHART DATA
chart_labels = [row['category'] for row in category_totals]
chart_values = [row['total'] for row in category_totals]

conn.close()

return render_template(
    "dashboard.html",
    name=session['name'],
    current_month=target_month,
    budget=budget_val,
    total=total_spent,
    remaining=remaining,
    status=status,
    highest_category=highest_category,
    suggestion=suggestion,
    data=expenses,
    categories=chart_labels,
    amounts=chart_values
)

# -------------------------------
# ADD EXPENSE
# -------------------------------

@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():

    if 'name' not in session:
        return redirect(url_for('index'))

    if request.method == "POST":

        date = request.form.get("date")
        category = request.form.get("category")
        amount = request.form.get("amount")

        if date and category and amount:
            conn = get_db_connection()

            conn.execute(
                "INSERT INTO expenses (name, date, category, amount) VALUES (?, ?, ?, ?)",
                (session['name'], date, category, float(amount))
            )

            conn.commit()
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template("add_expense.html")


# -------------------------------
# DOWNLOAD CSV
# -------------------------------

@app.route("/download")
def download():

    conn = sqlite3.connect("database.db")

    df = pd.read_sql_query("SELECT * FROM expenses", conn)

    conn.close()

    if df.empty:
        return "No data to download", 404

    file_path = "expense_report.csv"

    df.to_csv(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# -------------------------------
# RESET DATA
# -------------------------------

@app.route("/reset")
def reset():

    conn = get_db_connection()

    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM profile")

    conn.commit()
    conn.close()

    return redirect(url_for('index'))


# -------------------------------
# RUN APP
# -------------------------------

if __name__ == "__main__":
    app.run(debug=True)
