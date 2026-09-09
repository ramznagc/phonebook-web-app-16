from flask import Flask, request, render_template
from flaskext.mysql import MySQL
import boto3
import os

app = Flask(__name__)


def get_database_config():
    """Load database connection settings from environment variables or SSM."""
    endpoint_file = "/home/ec2-user/dbserver.endpoint"
    db_host = os.getenv("DB_HOST")
    if not db_host and os.path.exists(endpoint_file):
        with open(endpoint_file, "r", encoding="utf-8") as db_endpoint:
            db_host = db_endpoint.readline().strip()

    if not db_host:
        raise RuntimeError("DB_HOST is not configured and dbserver.endpoint was not found.")

    db_username = os.getenv("DB_USERNAME")
    db_password = os.getenv("DB_PASSWORD")

    if not db_username or not db_password:
        region = os.getenv("AWS_REGION", "eu-central-1")
        ssm = boto3.client("ssm", region_name=region)
        username_param = ssm.get_parameter(Name="/phonebook/db/username")
        password_param = ssm.get_parameter(Name="/phonebook/db/password", WithDecryption=True)
        db_username = username_param["Parameter"]["Value"]
        db_password = password_param["Parameter"]["Value"]

    return db_host, db_username, db_password


DB_HOST, DB_USERNAME, DB_PASSWORD = get_database_config()

app.config["MYSQL_DATABASE_HOST"] = DB_HOST
app.config["MYSQL_DATABASE_USER"] = DB_USERNAME
app.config["MYSQL_DATABASE_PASSWORD"] = DB_PASSWORD
app.config["MYSQL_DATABASE_DB"] = "ondia_phonebook"
app.config["MYSQL_DATABASE_PORT"] = 3306

mysql = MySQL()
mysql.init_app(app)


def get_cursor():
    connection = mysql.connect()
    connection.autocommit(True)
    return connection, connection.cursor()


def init_phonebook_db():
    connection, cursor = get_cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS phonebook (
                id INT NOT NULL AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                number VARCHAR(100) NOT NULL,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
    finally:
        cursor.close()
        connection.close()


def find_persons(keyword):
    connection, cursor = get_cursor()
    try:
        cursor.execute(
            "SELECT id, name, number FROM phonebook WHERE LOWER(name) LIKE %s",
            (f"%{keyword.strip().lower()}%",),
        )
        rows = cursor.fetchall()
        persons = [
            {"id": row[0], "name": row[1].strip().title(), "number": row[2]}
            for row in rows
        ]
        return persons or [{"name": "No Result", "number": "No Result"}]
    finally:
        cursor.close()
        connection.close()


def insert_person(name, number):
    connection, cursor = get_cursor()
    try:
        normalized_name = name.strip().lower()
        cursor.execute("SELECT id, name FROM phonebook WHERE name LIKE %s", (normalized_name,))
        row = cursor.fetchone()
        if row is not None:
            return f"Person with name {row[1].title()} already exists."
        cursor.execute(
            "INSERT INTO phonebook (name, number) VALUES (%s, %s)",
            (normalized_name, number),
        )
        return f"Person {name.strip().title()} added to Phonebook successfully"
    finally:
        cursor.close()
        connection.close()


def update_person(name, number):
    connection, cursor = get_cursor()
    try:
        normalized_name = name.strip().lower()
        cursor.execute("SELECT id, name FROM phonebook WHERE name LIKE %s", (normalized_name,))
        row = cursor.fetchone()
        if row is None:
            return f"Person with name {name.strip().title()} does not exist."
        cursor.execute("UPDATE phonebook SET number = %s WHERE id = %s", (number, row[0]))
        return f"Phone record of {name.strip().title()} is updated successfully"
    finally:
        cursor.close()
        connection.close()


def delete_person(name):
    connection, cursor = get_cursor()
    try:
        normalized_name = name.strip().lower()
        cursor.execute("SELECT id, name FROM phonebook WHERE name LIKE %s", (normalized_name,))
        row = cursor.fetchone()
        if row is None:
            return f"Person with name {name.strip().title()} does not exist, no need to delete."
        cursor.execute("DELETE FROM phonebook WHERE id = %s", (row[0],))
        return f"Phone record of {name.strip().title()} is deleted from the phonebook successfully"
    finally:
        cursor.close()
        connection.close()


@app.route("/", methods=["GET", "POST"])
def find_records():
    if request.method == "POST":
        keyword = request.form["username"]
        persons_app = find_persons(keyword)
        return render_template(
            "index.html",
            persons_html=persons_app,
            keyword=keyword,
            show_result=True,
            developer_name="Ramazan Agac",
        )
    return render_template("index.html", show_result=False, developer_name="Ramazan Agac")


@app.route("/add", methods=["GET", "POST"])
def add_record():
    if request.method == "POST":
        name = request.form["username"]
        if not name or not name.strip():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Name can not be empty", show_result=False, action_name="save", developer_name="Ramazan Agac")
        if name.isdecimal():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Name of person should be text", show_result=False, action_name="save", developer_name="Ramazan Agac")
        phone_number = request.form["phonenumber"]
        if not phone_number or not phone_number.strip():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Phone number can not be empty", show_result=False, action_name="save", developer_name="Ramazan Agac")
        if not phone_number.isdecimal():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Phone number should be in numeric format", show_result=False, action_name="save", developer_name="Ramazan Agac")
        result_app = insert_person(name, phone_number)
        return render_template("add-update.html", show_result=True, result_html=result_app, not_valid=False, action_name="save", developer_name="Ramazan Agac")
    return render_template("add-update.html", show_result=False, not_valid=False, action_name="save", developer_name="Ramazan Agac")


@app.route("/update", methods=["GET", "POST"])
def update_record():
    if request.method == "POST":
        name = request.form["username"]
        if not name or not name.strip():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Name can not be empty", show_result=False, action_name="update", developer_name="Ramazan Agac")
        phone_number = request.form["phonenumber"]
        if not phone_number or not phone_number.strip():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Phone number can not be empty", show_result=False, action_name="update", developer_name="Ramazan Agac")
        if not phone_number.isdecimal():
            return render_template("add-update.html", not_valid=True, message="Invalid input: Phone number should be in numeric format", show_result=False, action_name="update", developer_name="Ramazan Agac")
        result_app = update_person(name, phone_number)
        return render_template("add-update.html", show_result=True, result_html=result_app, not_valid=False, action_name="update", developer_name="Ramazan Agac")
    return render_template("add-update.html", show_result=False, not_valid=False, action_name="update", developer_name="Ramazan Agac")


@app.route("/delete", methods=["GET", "POST"])
def delete_record():
    if request.method == "POST":
        name = request.form["username"]
        if not name or not name.strip():
            return render_template("delete.html", not_valid=True, message="Invalid input: Name can not be empty", show_result=False, developer_name="Ramazan Agac")
        result_app = delete_person(name)
        return render_template("delete.html", show_result=True, result_html=result_app, not_valid=False, developer_name="Ramazan Agac")
    return render_template("delete.html", show_result=False, not_valid=False, developer_name="Ramazan Agac")


if __name__ == "__main__":
    init_phonebook_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "80")))
