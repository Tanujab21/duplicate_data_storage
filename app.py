from flask import Flask, render_template, request, redirect, flash
import boto3
import hashlib
import json
import os
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = "cloud-deduplication-secret"

# AWS configuration
AWS_REGION = "ap-south-1"
TABLE_NAME = "CloudDeduplication"
S3_BUCKET = "cloud-file-storage12"

# Connect to DynamoDB
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)

table = dynamodb.Table(TABLE_NAME)

# Connect to S3
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)


def create_record_hash(name, email, phone):
    """
    Create a unique SHA-256 hash from the record.
    """

    normalized_data = (
        name.strip().lower()
        + "|"
        + email.strip().lower()
        + "|"
        + phone.strip()
    )

    return hashlib.sha256(
        normalized_data.encode("utf-8")
    ).hexdigest()


def validate_record(name, email, phone):
    """
    Validate incoming data.
    """

    if not name or not email or not phone:
        return False, "All fields are required."

    if "@" not in email:
        return False, "Invalid email address."

    if len(phone) < 10:
        return False, "Invalid phone number."

    return True, "Valid"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/add", methods=["POST"])
def add_record():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    # Step 1: Validate data
    valid, message = validate_record(
        name,
        email,
        phone
    )

    if not valid:
        flash(message, "error")
        return redirect("/")

    # Step 2: Generate unique hash
    record_id = create_record_hash(
        name,
        email,
        phone
    )

    # Step 3: Check if record already exists
    try:

        response = table.get_item(
            Key={
                "record_id": record_id
            }
        )

        if "Item" in response:
            flash(
                "Duplicate record detected! Record was not stored.",
                "error"
            )

            return redirect("/")

        # Step 4: Store only unique data
        item = {
            "record_id": record_id,
            "name": name,
            "email": email,
            "phone": phone
        }

        table.put_item(
            Item=item
        )

        flash(
            "Record verified and stored successfully!",
            "success"
        )

    except ClientError as e:

        flash(
            "AWS error: " + e.response["Error"]["Message"],
            "error"
        )

    return redirect("/")


@app.route("/records")
def records():

    try:

        response = table.scan()

        items = response.get("Items", [])

        return render_template(
            "index.html",
            records=items
        )

    except ClientError as e:

        flash(
            "Unable to retrieve records: "
            + e.response["Error"]["Message"],
            "error"
        )

        return redirect("/")


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )