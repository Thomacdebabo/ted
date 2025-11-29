import glob
import os
from datetime import datetime
import shutil
import click
import yaml
from pydantic import BaseModel
from ted.config import VAULT_DIR, TODO_DIR, REF_DIR, DONE_DIR, PROJECTS_DIR, FILES_DIR
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
    get_next_id,
    prompt_todo_selection,
    prompt_project_selection,
    new_timestamp,
    find_todo_file,
    find_files,
)


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

    project_id = prompt_project_selection(PROJECTS_DIR)

    creation_timestamp = new_timestamp()
    next_id = get_next_id(TODO_DIR)

    _id = f"T{next_id:05d}"
    filename = f"{_id}_{name[:15].lower().replace(' ', '_')}.md"

    properties = Properties(
        created=creation_timestamp,
        id=_id,
        project_id=project_id if project_id else None,
    )

    tasks = [Task(done=False, description=next)]
    todo = TodoData(
        name=name, goal=goal, tasks=tasks, properties=properties, filename=filename
    )
    todo.write(TODO_DIR)


@cli.command()
def new_p():
    name = click.prompt("Enter the new project name", type=str)
    description = click.prompt("Enter project description", type=str)

    creation_timestamp = new_timestamp()
    next_id = get_next_id(PROJECTS_DIR)
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
    project.write(PROJECTS_DIR)


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
        shutil.copy(ref_content, os.path.join(FILES_DIR, ref_content))
    elif ref_type == ReferenceType.NOTEBOOK:
        ref_content = click.prompt("Enter the reference content", type=str)
        date = datetime.now().strftime("%Y-%m-%d")
        ref_content = f"Notebook: **{date}** {ref_content}"
    ref = create_reference(type=ref_type, content=ref_content)
    todo_id, todo, target_file = prompt_todo_selection(TODO_DIR)
    if not todo:
        click.echo("No valid todo selected for reference.")
        return
    tldr = click.prompt("Enter TLDR for the reference", type=str, default="")
    task = todo.filename
    next_id = get_next_id(REF_DIR)
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
    reference.write(REF_DIR)


@cli.command()
def block():
    click.echo("Select the todo to be blocked:")
    todo_id, todo, target_file = prompt_todo_selection(TODO_DIR)
    if not todo:
        click.echo("No valid todo selected for blocking.")
        return

    click.echo("Select the todo that blocks the first todo:")
    block_id, block_todo, block_file = prompt_todo_selection(TODO_DIR)
    if not block_todo:
        click.echo("No valid todo selected to block by.")
        return

    if todo.properties.blocked_by is None:
        todo.properties.blocked_by = []
    if block_todo.filename not in todo.properties.blocked_by:
        todo.properties.blocked_by.append(block_todo.filename)
        todo.write(TODO_DIR)
        click.echo(f"Todo {todo_id} is now blocked by {block_todo.filename}.")
    else:
        click.echo(f"Todo {todo_id} is already blocked by {block_todo.filename}.")


@cli.command()
@click.argument(
    "todo_id",
    required=False,
    default=None,
)
def update(todo_id):
    if todo_id is None:
        todo_id = prompt_todo_selection(TODO_DIR)[0]

    if todo_id is None:
        click.echo("No todo selected for update.")
        return

    todo_tuple = find_todo_file(todo_id, TODO_DIR)

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

    todo.write(TODO_DIR)

    click.echo(f"Updated todo {todo.id} and wrote changes to {target_file}")


@cli.command()
@click.option("-s", "--show", is_flag=True, help="Show details for each todo")
def ls(show):
    files = find_files(TODO_DIR)
    for file in files:
        try:
            todo = from_md_file(file)
            status = todo.status()
            click.echo(status)
            if show:
                click.echo(str(todo))
        except Exception as e:
            click.echo(f"Error reading {file}: {e}")


@cli.command()
@click.argument("todo_id")
def done(todo_id):
    todo_id, todo, target_file = prompt_todo_selection(TODO_DIR)

    if not todo:
        click.echo(f"Todo with ID {todo_id} not found.")
        return

    if not todo.is_completed():
        click.echo(f"Todo {todo_id} is not yet complete.")
        return

    todo.properties.completed = new_timestamp()

    if target_file is None:
        click.echo(f"Error: target file for todo {todo_id} not found.")
        return

    todo.write(DONE_DIR)

    os.remove(target_file)
    click.echo(f"Todo {todo_id} marked as done and moved to done directory.")


@cli.command()
@click.argument("todo_id")
def show(todo_id):
    todo_tuple = find_todo_file(todo_id, TODO_DIR)
    if not todo_tuple:
        click.echo(f"Todo with ID {todo_id} not found.")
        return
    todo, target_file = todo_tuple

    click.echo(str(todo))


@cli.command()
def status():
    files = find_files(TODO_DIR)
    for file in files:
        try:
            todo = from_md_file(file)
            click.echo(todo.status(verbose=True))
        except Exception as e:
            click.echo(f"Error reading {file}: {e}")


@cli.command()
def init():
    """Initialize the TED vault directories."""
    os.makedirs(TODO_DIR, exist_ok=True)
    os.makedirs(DONE_DIR, exist_ok=True)
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(REF_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    click.echo(f"Initialized TED vault at {VAULT_DIR}.")


def main():
    cli()


if __name__ == "__main__":
    main()
