import os
from datetime import datetime
import shutil
import click
import requests  # Added for HTTP requests
from ted.config import Config
from ted.data_types import (
    Properties,
    TodoData,
    ProjectData,
    ReferenceData,
    Task,
    ReferenceType,
    create_reference,
    InboxItem,
)
from ted.utils import (
    prompt_todo_selection,
    prompt_project_selection,
    new_timestamp,
    crop_filename,
)
from ted.data_types import from_md_file

from ted.vault import Vault

CONFIG = Config()
VAULT = Vault(CONFIG)
VAULT_DATA = VAULT.load_vault_data()


@click.group()
def cli():
    """TED - the todo buddy"""
    pass


@cli.command()
def new():
    """Create a new todo, project, or reference."""
    choice = click.prompt(
        "What would you like to create? (t)odo, (p)roject, (r)eference",
        type=click.Choice(["t", "p", "r"]),
    )
    choices = {"t": newt, "p": newp, "r": newr}
    ctx = click.get_current_context()
    ctx.invoke(choices[choice])


@cli.command()
def newt():
    name = click.prompt("Enter the new name", type=str)
    goal = click.prompt("Enter passing criteria", type=str)
    next = click.prompt("Next task to do", type=str)

    project = prompt_project_selection(VAULT_DATA.projects)

    creation_timestamp = new_timestamp()
    next_id = VAULT_DATA.get_next_id("todos")
    if project and project.shorthand:
        _id = f"{project.shorthand}{next_id:03d}"
    else:
        _id = f"T{next_id:05d}"
    filename = f"{_id}_{crop_filename(name)}.md"

    filepath = os.path.join(VAULT.required_dirs["todos"], filename)

    properties = Properties(
        created=creation_timestamp,
        id=_id,
        project_id=project.id if project else None,
    )

    tasks = [Task(done=False, description=next)]
    todo = TodoData(
        name=name,
        goal=goal,
        tasks=tasks,
        properties=properties,
        filename=filename,
        filepath=filepath,
    )
    todo.write(VAULT.required_dirs["todos"])


@cli.command()
def newp():
    name = click.prompt("Enter the new project name", type=str)
    description = click.prompt("Enter project description", type=str)
    shorthand = click.prompt(
        "Enter project shorthand (3 to 8 characters)",
        type=str,
        default="",
        show_default=False,
    )
    if shorthand and (len(shorthand) < 3 or len(shorthand) > 8):
        click.echo("Shorthand must be between 3 and 8 characters.")
        return

    shorthand = shorthand.upper()
    creation_timestamp = new_timestamp()
    next_id = VAULT_DATA.get_next_id("projects")
    _id = f"P{next_id:05d}_{shorthand}_{crop_filename(name)}"

    properties = Properties(id=_id, created=creation_timestamp)
    filename = _id + ".md"
    project = ProjectData(
        id=_id,
        name=name,
        shorthand=shorthand,
        description=description,
        properties=properties,
        filename=filename,
    )
    project.write(VAULT.required_dirs["projects"])


@cli.command()
def newr():
    type_str = click.prompt(
        "Enter reference type: ",
        type=click.Choice([t.value for t in ReferenceType]),
    )
    try:
        ref_type = ReferenceType(type_str)
    except ValueError:
        click.echo(f"Invalid reference type: {type_str}")
        return

    if ref_type == ReferenceType.LINK:
        ref_content = click.prompt("Enter the URL", type=str)
    elif ref_type == ReferenceType.FILE:
        ref_content = click.prompt("Enter the file path", type=str)
        if not os.path.isfile(ref_content):
            click.echo(f"File does not exist: {ref_content}")
            return
        ref_content = os.path.basename(ref_content)
        shutil.copy(ref_content, os.path.join(Config.FILES_DIR, ref_content))
    elif ref_type == ReferenceType.NOTEBOOK:
        ref_content = click.prompt("Enter the reference content", type=str)
        date = datetime.now().strftime("%Y-%m-%d")
        ref_content = f"Notebook: **{date}** {ref_content}"
    ref = create_reference(type=ref_type, content=ref_content)
    todo = prompt_todo_selection(VAULT_DATA.todos)

    if not todo:
        click.echo("No valid todo selected for reference.")
        return

    tldr = click.prompt("Enter TLDR for the reference", type=str, default="")
    task = todo.filename
    next_id = VAULT_DATA.get_next_id("references")
    _id = f"R{next_id:05d}"
    filename = f"{_id}.md"
    creation_timestamp = new_timestamp()
    properties = Properties(
        created=creation_timestamp,
        id=_id,
    )

    reference = ReferenceData(
        ref=ref,
        task=task,
        properties=properties,
        filename=filename,
        tldr=tldr,
    )
    reference.write(Config.REF_DIR)


@cli.command()
def block():
    click.echo("Select the todo to be blocked:")
    todo = prompt_todo_selection(VAULT_DATA.todos)
    if not todo:
        click.echo("No valid todo selected for blocking.")
        return

    click.echo("Select the todo that blocks the first todo:")
    block_todo = prompt_todo_selection(VAULT_DATA.todos)
    if not block_todo:
        click.echo("No valid todo selected to block by.")
        return

    if todo.properties.blocked_by is None:
        todo.properties.blocked_by = []
    if block_todo.filename not in todo.properties.blocked_by:
        todo.properties.blocked_by.append(block_todo.filename)
        todo.write(Config.TODO_DIR)
        click.echo(f"Todo {todo.id} is now blocked by {block_todo.filename}.")
    else:
        click.echo(f"Todo {todo.id} is already blocked by {block_todo.filename}.")


@cli.command()
@click.argument(
    "todo_id",
    required=False,
    default=None,
)
def update(todo_id):
    todos = VAULT_DATA.todos
    if todo_id is None:
        todo_id = prompt_todo_selection(todos)[0]

    if todo_id is None:
        click.echo("No todo selected for update.")
        return

    todo = VAULT_DATA.find("todos", todo_id)

    if not todo:
        click.echo(f"Todo with ID {todo_id} not found or invalid.")
        return

    click.echo(todo.status(verbose=True))

    selection = click.prompt(
        "Enter task numbers to mark done (space seperated), or leave empty for none",
        default="",
        show_default=False,
    ).strip()

    if selection:
        try:
            chosen = {int(s.strip()) for s in selection.split(" ") if s.strip()}
        except ValueError:
            click.echo("Invalid input. Please enter numbers separated by spaces.")
            return

        for num in sorted(chosen, reverse=True):
            if num < 0 or num > len(todo.tasks):
                click.echo(f"Ignoring invalid task number: {num}")
                continue
            todo.mark_task_done(num)

    next_task = click.prompt(
        "Next task to do (leave empty for none)", default="", show_default=False
    ).strip()
    if next_task:
        todo.add_task(next_task)

    extra_info = click.prompt(
        "Additional info to add (leave empty for none)", default="", show_default=False
    ).strip()

    if extra_info:
        todo.info.append(extra_info)

    todo.save()
    click.echo(f"Updated todo {todo.id} and wrote changes to {todo.filepath}")


@cli.command()
@click.argument(
    "todo_file",
    required=True,
    default=None,
)
def update_file(todo_file):
    if not os.path.isfile(todo_file):
        click.echo(f"File {todo_file} does not exist.")
        return
    todo = from_md_file(todo_file)

    if not todo:
        click.echo(f"Todo with ID {todo_file} not found or invalid.")
        return

    click.echo(todo.status(verbose=True))

    selection = click.prompt(
        "Enter task numbers to mark done (space seperated), or leave empty for none",
        default="",
        show_default=False,
    ).strip()

    if selection:
        try:
            chosen = {int(s.strip()) for s in selection.split(" ") if s.strip()}
        except ValueError:
            click.echo("Invalid input. Please enter numbers separated by spaces.")
            return

        for num in sorted(chosen, reverse=True):
            if num < 0 or num > len(todo.tasks):
                click.echo(f"Ignoring invalid task number: {num}")
                continue
            todo.mark_task_done(num)

    next_task = click.prompt(
        "Next task to do (leave empty for none)", default="", show_default=False
    ).strip()
    if next_task:
        todo.add_task(next_task)

    extra_info = click.prompt(
        "Additional info to add (leave empty for none)", default="", show_default=False
    ).strip()

    if extra_info:
        todo.info.append(extra_info)

    todo.save()
    click.echo(f"Updated todo {todo.id} and wrote changes to {todo.filepath}")


@cli.command()
@click.option("-s", "--show", is_flag=True, help="Show details for each todo")
@click.option("-t", "--tag", is_flag=True, help="Filter todos by tags")
def ls(show, tag):
    todos = VAULT_DATA.todos
    tag_dict = {}
    if tag:
        for todo in todos:
            tags = todo.tags
            for tag in tags:
                t = tag_dict.get(tag, [])
                t.append(todo)
                tag_dict[tag] = t

        for tag, tag_todos in tag_dict.items():
            click.echo(f"Tag: {tag} - {len(tag_todos)} todos")
            for todo in tag_todos:
                status = todo._status().value
                click.echo(f"  {status} {todo.id}: {todo.name}")
                if show:
                    click.echo(str(todo))
    else:
        file_paths = []
        for todo in todos:
            relative_path = os.path.dirname(
                os.path.relpath(todo.filepath, Config.TODO_DIR)
            )
            file_paths.append((relative_path, todo))

        file_paths.sort(key=lambda x: x[0])
        last_relative_path = ""
        for relative_path, todo in file_paths:
            if relative_path != last_relative_path:
                click.echo(f"\nDirectory: {relative_path}")
                last_relative_path = relative_path
            status = todo._status().value
            click.echo(f"{status} {todo.id}: {todo.name}")
            if show:
                click.echo(str(todo))


@cli.command()
@click.argument("todo_id")
def done(todo_id):
    todo = VAULT_DATA.find("todos", todo_id)

    if not todo:
        click.echo(f"Todo with ID {todo.id} not found.")
        return

    if not todo.is_completed():
        click.echo(f"Todo {todo.id} is not yet complete.")
        for i, task in enumerate(todo.tasks):
            if not task.done:
                click.echo(f" - Task {i}: {task.description} [NOT DONE]")
        confirm = click.prompt("y to confirm marking as done", type=str)
        if confirm.lower() != "y":
            return
        todo.mark_all_done()

    todo.properties.completed = new_timestamp()

    todo.write(Config.DONE_DIR)

    os.remove(todo.filepath)
    click.echo(f"Todo {todo.id} marked as done and moved to done directory.")


@cli.command()
@click.argument("todo_file")
def done_file(todo_file):
    if not os.path.isfile(todo_file):
        click.echo(f"File {todo_file} does not exist.")
        return

    todo = from_md_file(todo_file)

    if not todo:
        click.echo(f"Todo with ID {todo.id} not found.")
        return

    if not todo.is_completed():
        click.echo(f"Todo {todo.id} is not yet complete.")
        for i, task in enumerate(todo.tasks):
            if not task.done:
                click.echo(f" - Task {i}: {task.description} [NOT DONE]")
        confirm = click.prompt("y to confirm marking as done", type=str)
        if confirm.lower() != "y":
            return
        todo.mark_all_done()

    todo.properties.completed = new_timestamp()

    todo.write(Config.DONE_DIR)

    os.remove(todo.filepath)
    click.echo(f"Todo {todo.id} marked as done and moved to done directory.")


@cli.command()
@click.argument("todo_id")
def show(todo_id):
    todo = VAULT_DATA.find("todos", todo_id)
    if not todo:
        click.echo(f"Todo with ID {todo_id} not found.")
        return
    click.echo(str(todo))


@cli.command()
@click.argument("todo_file")
def show_file(todo_file):
    if not os.path.isfile(todo_file):
        click.echo(f"File {todo_file} does not exist.")
        return

    todo = from_md_file(todo_file)

    if not todo:
        click.echo(f"Todo with ID {todo_file} not found.")
        return
    click.echo(str(todo))

@cli.command()
@click.argument("todo_file")
def id(todo_file):
    if not os.path.isfile(todo_file):
        return

    todo = from_md_file(todo_file)

    if not todo:
        return
    click.echo(str(todo.id))


@cli.command()
def status():
    todos = VAULT.load_todos()
    for todo in todos:
        try:
            click.echo(todo.status(verbose=True))
        except Exception as e:
            click.echo(f"Error reading {todo.filepath}: {e}")


@cli.command()
def init():
    """Initialize the TED vault directories."""
    Config.init()
    click.echo(f"Initialized TED vault at {Config.VAULT_DIR}.")


@cli.command()
def inbox():
    """Retrieve inbox items from the inbox server and save to local inbox directory."""
    url = CONFIG.INBOX_SERVER_URL  # Assumes this is defined in Config
    inbox_dir = CONFIG.INBOX_DIR  # Assumes this is defined in Config

    url = url.rstrip("/") + "/api/items"

    try:
        response = requests.get(url)
        response.raise_for_status()
        if "application/json" not in response.headers.get("content-type", ""):
            click.echo(
                f"Server did not return JSON. Response: {response.text[:500]}..."
            )
            return
        items = response.json()["items"]
    except requests.RequestException as e:
        click.echo(f"Error fetching inbox items: {e}")
        return
    except ValueError as e:
        click.echo(f"Invalid JSON received: {e}. Response: {response.text[:500]}...")
        return

    os.makedirs(inbox_dir, exist_ok=True)
    photos_dir = os.path.join(inbox_dir, "photos")
    files_dir = os.path.join(inbox_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    os.makedirs(photos_dir, exist_ok=True)

    for item in items:
        filename, content = item["filename"], item["content"]
        filepath = os.path.join(inbox_dir, filename)
        inbox_item = InboxItem.model_validate_json(content)

        # Download photo if it exists
        if inbox_item.photo:
            photo_url = (
                CONFIG.INBOX_SERVER_URL.rstrip("/") + f"/uploads/{inbox_item.photo}"
            )
            dest_photo_path = os.path.join(photos_dir, inbox_item.photo)
            try:
                photo_response = requests.get(photo_url)
                photo_response.raise_for_status()
                with open(dest_photo_path, "wb") as photo_file:
                    photo_file.write(photo_response.content)
                click.echo(f"Downloaded photo {inbox_item.photo}")
            except requests.RequestException as e:
                click.echo(f"Error downloading photo {inbox_item.photo}: {e}")
        if inbox_item.file:
            file_url = (
                CONFIG.INBOX_SERVER_URL.rstrip("/") + f"/uploads/{inbox_item.file}"
            )
            dest_file_path = os.path.join(files_dir, inbox_item.file)
            try:
                file_response = requests.get(file_url)
                file_response.raise_for_status()
                with open(dest_file_path, "wb") as data_file:
                    data_file.write(file_response.content)
                click.echo(f"Downloaded file {inbox_item.file}")
            except requests.RequestException as e:
                click.echo(f"Error downloading file {inbox_item.file}: {e}")
        with open(filepath, "w") as f:
            f.write(str(inbox_item))
        click.echo(f"Saved inbox item {inbox_item.id} to {filepath}")
    clear_inbox = click.prompt(
        "Clear inbox on server? (y/n)",
        type=click.Choice(["y", "n"]),
        default="n",
    )
    if clear_inbox == "y":
        try:
            clear_url = CONFIG.INBOX_SERVER_URL.rstrip("/") + "/api/clear"
            clear_response = requests.post(clear_url)
            clear_response.raise_for_status()
            click.echo("Inbox cleared on server.")
        except requests.RequestException as e:
            click.echo(f"Error clearing inbox on server: {e}")


def main():
    cli()


if __name__ == "__main__":
    main()
