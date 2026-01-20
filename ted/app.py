import os
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    send_from_directory,
)
from ted.utils import new_timestamp, crop_filename
from ted.data_types import InboxItem, inbox_from_md

app = Flask(__name__)

INBOX_DIR = os.environ.get("TED_INBOX_DIR")
UPLOAD_DIR = os.environ.get("TED_UPLOAD_DIR")

if not INBOX_DIR:
    INBOX_DIR = os.path.expanduser("~/.ted-server/inbox")
os.makedirs(INBOX_DIR, exist_ok=True)

if not UPLOAD_DIR:
    UPLOAD_DIR = os.path.expanduser("~/.ted-server/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

print(f"Using INBOX_DIR: {INBOX_DIR}")
print(f"Using UPLOAD_DIR: {UPLOAD_DIR}")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/add", methods=["POST"])
def add():
    item = request.form.get("item")
    photo = request.files.get("photo")
    file = request.files.get("file")
    title = request.form.get("title")

    # Generate randomized ID
    timestamp = new_timestamp()

    cropped_title = crop_filename(title, max_length=12)
    inbox_id = f"{timestamp}_{cropped_title}"
    photo_filename = None
    file_filename = None
    # Fix: Check if photo exists and filename is not empty string
    if photo and photo.filename and photo.filename != "":
        photo_filename = f"photo_{inbox_id}_{photo.filename}"
        photo_path = os.path.join(UPLOAD_DIR, photo_filename)
        photo.save(photo_path)

    if file and file.filename and file.filename != "":
        file_filename = f"file_{inbox_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, file_filename)
        file.save(file_path)

    inbox_item = InboxItem(
        title=title,
        content=item,
        timestamp=timestamp,
        id=inbox_id,
        photo=photo_filename,
        file=file_filename,
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
