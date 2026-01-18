from datetime import datetime

import click

from ted.data_types import (
    TodoData,
    ProjectData,
)


def new_timestamp():
    return datetime.now().strftime("%m-%d-%Y_%H:%M:%S")


def prompt_project_selection(projects: list[ProjectData]):
    if not projects:
        return None
    click.echo("Available project files: ")
    for i, project in enumerate(projects):
        click.echo(f"{i+1}. {project.shorthand} {project.name}")

    project_idx = click.prompt(
        "Project ID (leave empty for none)", default="", show_default=False
    ).strip()

    if project_idx == "":
        click.echo("None selected.")
        return None

    if int(project_idx) <= 0 or int(project_idx) > len(projects):
        click.echo("Invalid project selection. Proceeding without a project.")
        return None
    return projects[int(project_idx) - 1]

def prompt_todo_selection(todos: list[TodoData]) -> TodoData | None:
    if not todos:
        return None
    click.echo("Available todo files: ")
    for i, todo in enumerate(todos):
        click.echo(f"{i+1}. {todo.name}")
    todo_idx = click.prompt(
        "Todo ID (leave empty for none)", default="", show_default=False
    ).strip()

    if not todo_idx:
        click.echo("None selected.")
        return None

    if int(todo_idx) <= 0 or int(todo_idx) > len(todos):
        click.echo("Invalid todo selection. Proceeding without a todo.")
        return None

    return todos[int(todo_idx) - 1]
def crop_filename(filename: str, max_length: int = 20) -> str:
    if len(filename) <= max_length:
        return filename
    else:
        split_filename = filename.split(" ")
        for i in range(1, len(split_filename)):
            if len("_".join(split_filename[:-i])) <= max_length:
                return "_".join(split_filename[:-i])

        return filename[:max_length]  # Fallback: return last max_length characters
