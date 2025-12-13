import glob
import os
from datetime import datetime
import shutil
import click
import yaml
from pydantic import BaseModel
from ted.config import Config
from ted.types import (
    Properties,
    StatusSymbols,
    TodoData,
    ProjectData,
    ReferenceData,
    Task,
    Reference,
    ReferenceType,
    create_reference,
    from_md_file,
)
from ted.utils import (
    prompt_todo_selection,
    prompt_project_selection,
    new_timestamp,
    find_todo_file,
)

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
    choices = {"t": new_t, "p": new_p, "r": new_ref}
    ctx = click.get_current_context()
    ctx.invoke(choices[choice])


@cli.command()
def new_t():
    name = click.prompt("Enter the new name", type=str)
    goal = click.prompt("Enter passing criteria", type=str)
    next = click.prompt("Next task to do", type=str)

    project_id = prompt_project_selection(Config.PROJECTS_DIR)

    creation_timestamp = new_timestamp()
    next_id = VAULT_DATA.get_next_id("todos")

    _id = f"T{next_id:05d}"
    filename = f"{_id}_{name[:15].lower().replace(' ', '_')}.md"

    filepath = os.path.join(VAULT.required_dirs["todos"], filename)

    properties = Properties(
        created=creation_timestamp,
        id=_id,
        project_id=project_id if project_id else None,
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
def new_p():
    name = click.prompt("Enter the new project name", type=str)
    description = click.prompt("Enter project description", type=str)

    creation_timestamp = new_timestamp()
    next_id = VAULT_DATA.get_next_id("projects")
    _id = f"P{next_id:05d}"

    properties = Properties(id=_id, created=creation_timestamp)
    filename = _id + ".md"
    project = ProjectData(
        id=_id,
        name=name,
        description=description,
        properties=properties,
        filename=filename,
    )
    project.write(VAULT.required_dirs["projects"])


@cli.command()
def new_ref():
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
    if todo_id is None:
        todo_id = prompt_todo_selection(Config.TODO_DIR)[0]

    if todo_id is None:
        click.echo("No todo selected for update.")
        return

    todo_tuple = find_todo_file(todo_id, Config.TODO_DIR)

    if not todo_tuple or todo_tuple[0] is None or todo_tuple[1] is None:
        click.echo(f"Todo with ID {todo_id} not found or invalid.")
        return

    todo, target_file = todo_tuple

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

    todo.write(Config.TODO_DIR)

    click.echo(f"Updated todo {todo.id} and wrote changes to {target_file}")


@cli.command()
@click.option("-s", "--show", is_flag=True, help="Show details for each todo")
def ls(show):
    todos = VAULT_DATA.todos
    tag_dict = {}

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


@cli.command()
def done():
    todo = prompt_todo_selection(VAULT_DATA.todos)

    if not todo:
        click.echo(f"Todo with ID {todo.id} not found.")
        return

    if not todo.is_completed():
        click.echo(f"Todo {todo.id} is not yet complete.")
        return

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
def vault():
    """Access the TED vault."""
    v = Vault(Config)
    vault_data = v.load_vault_data()
    t = vault_data.find("todos", "T00001")
    todos = v.load_todos()
    v.print_todos(todos)
    print(t)


def main():
    cli()


if __name__ == "__main__":
    main()
