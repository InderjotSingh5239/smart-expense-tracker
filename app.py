from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import pandas as pd

app = Flask(__name__)

# -------------------------------
# DATABASE INITIALIZATION
# -------------------------------

def init_db():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        budget REAL,
        date TEXT,
        category TEXT,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------------
# HOME PAGE (ADD EXPENSE)
# -------------------------------

@app.route("/", methods=["GET","POST"])
def index():

    if request.method == "POST":

        name = request.form["name"]
        budget = request.form["budget"]
        date = request.form["date"]
        category = request.form["category"]
        amount = request.form["amount"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
        "INSERT INTO expenses(name,budget,date,category,amount) VALUES (?,?,?,?,?)",
        (name,budget,date,category,amount)
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("index.html")


# -------------------------------
# DASHBOARD
# -------------------------------

@app.route("/dashboard")
def dashboard():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # get all records
    cur.execute("SELECT * FROM expenses")
    data = cur.fetchall()

    # calculate total expenses
    cur.execute("SELECT SUM(amount) FROM expenses")
    total = cur.fetchone()[0]

    if total is None:
        total = 0

    # get budget
    cur.execute("SELECT budget FROM expenses LIMIT 1")
    budget_data = cur.fetchone()

    if budget_data:
        budget = budget_data[0]
    else:
        budget = 0

    # remaining budget
    remaining = budget - total

    # category analysis
    cur.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
    category_data = cur.fetchall()

    conn.close()

    categories = [row[0] for row in category_data]
    amounts = [row[1] for row in category_data]

    # find highest spending category
    highest_category = ""
    highest_amount = 0

    for row in category_data:

        if row[1] > highest_amount:
            highest_amount = row[1]
            highest_category = row[0]

    # suggestions
    suggestion = ""

    if highest_category == "Food":
        suggestion = "Try cooking at home more often."
    elif highest_category == "Travel":
        suggestion = "Use public transport to reduce travel costs."
    elif highest_category == "Shopping":
        suggestion = "Avoid impulse buying and set a shopping limit."
    elif highest_category == "Bills":
        suggestion = "Try reducing electricity and water usage."

    # budget status
    if total > budget:
        status = "You exceeded your budget!"
    else:
        status = " You are within your budget."

    return render_template(
        "dashboard.html",
        data=data,
        total=total,
        budget=budget,
        remaining=remaining,
        status=status,
        categories=categories,
        amounts=amounts,
        highest_category=highest_category,
        highest_amount=highest_amount,
        suggestion=suggestion
    )


# -------------------------------
# DOWNLOAD REPORT
# -------------------------------

@app.route("/download")
def download():

    conn = sqlite3.connect("database.db")

    df = pd.read_sql_query("SELECT * FROM expenses", conn)

    conn.close()

    file = "expense_report.csv"

    df.to_csv(file, index=False)

    return send_file(file, as_attachment=True)


# -------------------------------
# RUN SERVER
# -------------------------------

if __name__ == "__main__":
    app.run(debug=True)
