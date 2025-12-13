import glob
import os
from datetime import datetime

import click
import yaml
from pydantic import BaseModel

from ted.types import (
    Properties,
    TodoData,
    ProjectData,
    ReferenceData,
    Task,
    Reference,
    ReferenceType,
    from_md_file,
)


def find_files(dir):
    files = glob.glob(os.path.join(dir, "[A-Z][0-9]*.md"))
    files.sort()
    return files


def new_timestamp():
    return datetime.now().strftime("%m-%d-%Y_%H:%M:%S")


def find_todo_file(todo_id: str, todo_dir: str):
    files = find_files(todo_dir)
    target_file = None
    for file in files:
        if os.path.basename(file).startswith(todo_id):
            target_file = file
            break

    if not target_file:
        click.echo(f"Todo with ID {todo_id} not found.")
        return None, None
    else:
        click.echo(f"Found todo file: {target_file}")
    return from_md_file(target_file), target_file


def prompt_project_selection(project_dir: str):
    project_files = find_files(project_dir)
    if project_files:
        click.echo("Available project files: ")
        for i, pf in enumerate(project_files):
            project = from_md_file(pf)
            click.echo(f"{i}. {os.path.basename(pf)} - {project.name}")
        project_idx = click.prompt(
            "Project ID (leave empty for none)", default="", show_default=False
        ).strip()
    else:
        project_idx = ""

    if project_idx != "":
        try:
            project_idx = int(project_idx)
            project_file = project_files[project_idx]
            project = from_md_file(project_file)
            project_id = project.id
        except (ValueError, IndexError):
            click.echo("Invalid project selection. Proceeding without a project.")
            project_id = None
    else:
        project_id = None
    return project_id


def prompt_todo_selection(todos: list[TodoData]):
    if todos:
        click.echo("Available todo files: ")
        for i, todo in enumerate(todos):
            click.echo(f"{i}. {todo.name}")
        todo_idx = click.prompt(
            "Todo ID (leave empty for none)", default="", show_default=False
        ).strip()
    else:
        todo_idx = ""

    if todo_idx != "":
        try:
            todo_idx = int(todo_idx)
            todo = todos[todo_idx]
        except (ValueError, IndexError):
            click.echo("Invalid todo selection. Proceeding without a todo.")
            todo = None

    return todo
