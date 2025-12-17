import os
import secrets
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    send_from_directory,
)
from ted.utils import new_timestamp
from ted.data_types import InboxItem, inbox_from_md

app = Flask(__name__)


INBOX_DIR = os.path.expanduser("~/.ted-server/inbox")
UPLOAD_DIR = os.path.expanduser("~/.ted-server/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/add", methods=["POST"])
def add():
    item = request.form.get("item")
    photo = request.files.get("photo")

    # Generate randomized ID
    random_id = secrets.token_hex(4).upper()  # 8 character hex string
    inbox_id = f"I{random_id}"
    timestamp = new_timestamp()

    photo_filename = None
    # Fix: Check if photo exists and filename is not empty string
    if photo and photo.filename and photo.filename != "":
        photo_filename = f"photo_{random_id}_{photo.filename}"
        photo_path = os.path.join(UPLOAD_DIR, photo_filename)
        photo.save(photo_path)
    else:
        pass  # No photo uploaded

    inbox_item = InboxItem(
        content=item, timestamp=timestamp, id=inbox_id, photo=photo_filename
    )
    filename = f"{inbox_item.id}_{timestamp.replace(':', '').replace('-', '').replace(' ', '_')}.md"
    filepath = os.path.join(INBOX_DIR, filename)
    with open(filepath, "w") as f:
        f.write(str(inbox_item))
    return redirect(url_for("index"))


@app.route("/api/items", methods=["GET"])
def get_items():
    items = []
    try:
        for filename in sorted(os.listdir(INBOX_DIR)):
            filepath = os.path.join(INBOX_DIR, filename)
            if os.path.isfile(filepath):
                with open(filepath, "r") as f:
                    content = f.read()
                    inbox_item = inbox_from_md(content)
                items.append(
                    {"filename": filename, "content": inbox_item.model_dump_json()}
                )
        return {"items": items}
    except FileNotFoundError:
        pass
    return {"items": items}


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded photos."""
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/api/clear", methods=["POST"])
def clear_items():
    """Clear all inbox items and uploaded photos."""
    try:
        # Delete all markdown files in inbox
        for filename in os.listdir(INBOX_DIR):
            filepath = os.path.join(INBOX_DIR, filename)
            if os.path.isfile(filepath) and filename.endswith(".md"):
                os.remove(filepath)

        # Delete all photos in uploads
        for filename in os.listdir(UPLOAD_DIR):
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)

        return {"status": "success", "message": "All items cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


if __name__ == "__main__":
    # Development only
    app.run(host="0.0.0.0", debug=True)
