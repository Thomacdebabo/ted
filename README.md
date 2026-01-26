# TED - the todo buddy
The idea is to have a little cli interface which allows you to create and manage tasks fairly quickly.
- I need something that is quite fast and easy to use. 
- It should export .md files in obsidian format
- It is based on things I read in in [[Getting things done by david allen]] where you think a bit more about your todos so they include:
	- **name**: What you want to do
	- **goal**: basically what the conditions are to consider it done
	- **next step**: what the next thing you should be doing is, something that you could do
- Dataformat is a dictionary which uses titles to define key value pairs


# Setup
```
uv sync
source .venv/bin/activate
./install.sh
```

Dev setup:
```
uv pip install -e .

```
-> ted-dev
# aliases
```bash
# find .md files
find ~/.ted/**/*.md | fzf


find ~/.ted/**/*.md | xargs -n1 basename | fzf

find ~/.ted -name "*.md" | sed "s|^$HOME/.ted/||" | fzf

# for bashrc
fted() {
    local selected
    selected=$(find $HOME/.ted/todos/ -name "*.md" | sed "s|^$HOME/.ted/||" | fzf)
    
    if [[ -n "$selected" ]]; then
        echo "$HOME/.ted/$selected"
    fi
}

upted() {
	ted update-file $(fted)
}

donted() {
	ted done-file $(fted)
}
sted() {
	ted show-file $(fted)
}

fzit() {
  zit start $(ted id $(fted))
}

```

# Ted inbox server

The TED Inbox provides a web interface for quickly capturing notes, todos, and ideas.

## Run server (Docker)
1. ```bash
	docker build . -t ted
	docker run -d -p 5000:5000 ted
	```
## How to run Dev TED Inbox

1. **Install dependencies** (if not already done):
	```bash
	uv sync
	source .venv/bin/activate
	./install.sh
	```


2. **Start the inbox server with Gunicorn (development):**
	```bash
	uv run ./ted/app.py
	```
	By default, the server will run on http://0.0.0.0:5000

3. **Open your browser** and go to:
	```
	http://localhost:5000
	```
	to access the TED Inbox web interface.

You can now add notes with a required title and optional description, and attach files or photos if needed.
