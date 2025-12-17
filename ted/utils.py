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
        click.echo(f"{i}. {project.shorthand} {project.name}")

    project_idx = click.prompt(
        "Project ID (leave empty for none)", default="", show_default=False
    ).strip()

    if project_idx == "":
        click.echo("None selected.")
        return None

    if int(project_idx) < 0 or int(project_idx) >= len(projects):
        click.echo("Invalid project selection. Proceeding without a project.")
        return None
    return projects[int(project_idx)]


def prompt_todo_selection(todos: list[TodoData]) -> TodoData | None:
    if not todos:
        return None
    click.echo("Available todo files: ")
    for i, todo in enumerate(todos):
        click.echo(f"{i}. {todo.name}")
    todo_idx = click.prompt(
        "Todo ID (leave empty for none)", default="", show_default=False
    ).strip()

    if not todo_idx:
        click.echo("None selected.")
        return None

    if int(todo_idx) < 0 or int(todo_idx) >= len(todos):
        click.echo("Invalid todo selection. Proceeding without a todo.")
        return None

    return todos[int(todo_idx)]
