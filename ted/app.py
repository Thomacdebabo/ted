import json
import os
from flask import Flask, request, render_template_string
from pydantic import BaseModel
from ted.utils import new_timestamp
from ted.types import InboxItem, inbox_from_md
app = Flask(__name__)


INBOX_DIR = os.path.expanduser("~/.ted-server/inbox")


@app.route("/", methods=["GET"])
def index():
    html = """
    <html>
    <head>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #333; }
        textarea { 
            width: 400px; 
            height: 200px; 
            padding: 12px; 
            font-size: 16px; 
            border: 2px solid #ddd;
            border-radius: 4px;
            resize: none;
        }
        textarea:focus { 
            outline: none; 
            border-color: #4CAF50;
        }
        button { 
            padding: 12px 24px; 
            font-size: 16px; 
            background-color: #4CAF50; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }
        button:hover { background-color: #45a049; }
    </style>
    </head>
    <body>
    <h1>TED Inbox</h1>
    <form action="/add" method="post">
        <textarea name="item" placeholder="Add idea/todo" required></textarea>
        <button type="submit">Add</button>
    </form>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/add", methods=["POST"])
def add():
    item = request.form.get("item")
    next_id = len(os.listdir(INBOX_DIR)) + 1
    timestamp = new_timestamp()
    inbox_item = InboxItem(content=item, timestamp=timestamp, id=f"I{next_id:05d}")
    filename = f"{inbox_item.id}_{timestamp.replace(':', '').replace('-', '').replace(' ', '_')}.md"
    filepath = os.path.join(INBOX_DIR, filename)
    with open(filepath, "w") as f:
        f.write(str(inbox_item))
    return index()


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


if __name__ == "__main__":
    app.run(debug=True)
