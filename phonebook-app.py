from flask import Flask, request, render_template
import os
import sqlite3

try:
    import pymysql
except ImportError:
    pymysql = None

app = Flask(__name__)


def use_mysql():
    return bool(os.getenv("DB_HOST"))


def get_db():
    """Use AWS RDS MySQL when DB_HOST is set; otherwise use local SQLite."""
    if use_mysql():
        if pymysql is None:
            raise RuntimeError("PyMySQL is required for the MySQL/RDS configuration.")
        return pymysql.connect(
            host=os.environ["DB_HOST"],
            user=os.getenv("DB_USERNAME", "admin"),
            password=os.environ["DB_PASSWORD"],
            database=os.getenv("DB_NAME", "ondia_phonebook"),
            port=int(os.getenv("DB_PORT", "3306")),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    connection = sqlite3.connect("phonebook.db")
    connection.row_factory = sqlite3.Row
    return connection


def init_phonebook_db():
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS phonebook (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                number VARCHAR(100) NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def find_persons(keyword):
    connection = get_db()
    try:
        cursor = connection.cursor()
        pattern = f"%{keyword.strip().lower()}%"
        if use_mysql():
            cursor.execute("SELECT id, name, number FROM phonebook WHERE LOWER(name) LIKE %s", (pattern,))
        else:
            cursor.execute("SELECT id, name, number FROM phonebook WHERE LOWER(name) LIKE ?", (pattern,))
        rows = cursor.fetchall()
        persons = [
            {"id": row["id"], "name": row["name"].strip().title(), "number": row["number"]}
            for row in rows
        ]
        return persons or [{"name": "No Result", "number": "No Result"}]
    finally:
        connection.close()


def insert_person(name, number):
    connection = get_db()
    try:
        cursor = connection.cursor()
        normalized_name = name.strip().lower()
        if use_mysql():
            cursor.execute("SELECT id, name FROM phonebook WHERE name = %s", (normalized_name,))
        else:
            cursor.execute("SELECT id, name FROM phonebook WHERE name = ?", (normalized_name,))
        row = cursor.fetchone()
        if row:
            return f"Person with name {row['name'].title()} already exists."

        if use_mysql():
            cursor.execute("INSERT INTO phonebook (name, number) VALUES (%s, %s)", (normalized_name, number))
        else:
            cursor.execute("INSERT INTO phonebook (name, number) VALUES (?, ?)", (normalized_name, number))
        connection.commit()
        return f"Person {name.strip().title()} added to Phonebook successfully"
    finally:
        connection.close()


def update_person(name, number):
    connection = get_db()
    try:
        cursor = connection.cursor()
        normalized_name = name.strip().lower()
        if use_mysql():
            cursor.execute("SELECT id, name FROM phonebook WHERE name = %s", (normalized_name,))
        else:
            cursor.execute("SELECT id, name FROM phonebook WHERE name = ?", (normalized_name,))
        row = cursor.fetchone()
        if not row:
            return f"Person with name {name.strip().title()} does not exist."

        if use_mysql():
            cursor.execute("UPDATE phonebook SET number = %s WHERE id = %s", (number, row["id"]))
        else:
            cursor.execute("UPDATE phonebook SET number = ? WHERE id = ?", (number, row["id"]))
        connection.commit()
        return f"Phone record of {name.strip().title()} is updated successfully"
    finally:
        connection.close()


def delete_person(name):
    connection = get_db()
    try:
        cursor = connection.cursor()
        normalized_name = name.strip().lower()
        if use_mysql():
            cursor.execute("SELECT id, name FROM phonebook WHERE name = %s", (normalized_name,))
        else:
            cursor.execute("SELECT id, name FROM phonebook WHERE name = ?", (normalized_name,))
        row = cursor.fetchone()
        if not row:
            return f"Person with name {name.strip().title()} does not exist, no need to delete."

        if use_mysql():
            cursor.execute("DELETE FROM phonebook WHERE id = %s", (row["id"],))
        else:
            cursor.execute("DELETE FROM phonebook WHERE id = ?", (row["id"],))
        connection.commit()
        return f"Phone record of {name.strip().title()} is deleted successfully"
    finally:
        connection.close()


@app.route("/", methods=["GET", "POST"])
def find_records():
    if request.method == "POST":
        keyword = request.form.get("username", "")
        return render_template(
            "index.html",
            persons_html=find_persons(keyword),
            keyword=keyword,
            show_result=True,
            developer_name="Ramazan Agac",
        )
    return render_template("index.html", show_result=False, developer_name="Ramazan Agac")


@app.route("/add", methods=["GET", "POST"])
def add_record():
    if request.method == "POST":
        name = request.form.get("username", "")
        number = request.form.get("phonenumber", "")
        if not name.strip():
            message = "Invalid input: Name can not be empty"
        elif name.isdecimal():
            message = "Invalid input: Name of person should be text"
        elif not number.strip():
            message = "Invalid input: Phone number can not be empty"
        elif not number.isdecimal():
            message = "Invalid input: Phone number should be in numeric format"
        else:
            return render_template("add-update.html", show_result=True, result_html=insert_person(name, number), not_valid=False, action_name="save", developer_name="Ramazan Agac")
        return render_template("add-update.html", not_valid=True, message=message, show_result=False, action_name="save", developer_name="Ramazan Agac")
    return render_template("add-update.html", show_result=False, not_valid=False, action_name="save", developer_name="Ramazan Agac")


@app.route("/update", methods=["GET", "POST"])
def update_record():
    if request.method == "POST":
        name = request.form.get("username", "")
        number = request.form.get("phonenumber", "")
        if not name.strip():
            message = "Invalid input: Name can not be empty"
        elif not number.strip():
            message = "Invalid input: Phone number can not be empty"
        elif not number.isdecimal():
            message = "Invalid input: Phone number should be in numeric format"
        else:
            return render_template("add-update.html", show_result=True, result_html=update_person(name, number), not_valid=False, action_name="update", developer_name="Ramazan Agac")
        return render_template("add-update.html", not_valid=True, message=message, show_result=False, action_name="update", developer_name="Ramazan Agac")
    return render_template("add-update.html", show_result=False, not_valid=False, action_name="update", developer_name="Ramazan Agac")


@app.route("/delete", methods=["GET", "POST"])
def delete_record():
    if request.method == "POST":
        name = request.form.get("username", "")
        if not name.strip():
            return render_template("delete.html", not_valid=True, message="Invalid input: Name can not be empty", show_result=False, developer_name="Ramazan Agac")
        return render_template("delete.html", show_result=True, result_html=delete_person(name), not_valid=False, developer_name="Ramazan Agac")
    return render_template("delete.html", show_result=False, not_valid=False, developer_name="Ramazan Agac")


if __name__ == "__main__":
    init_phonebook_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
