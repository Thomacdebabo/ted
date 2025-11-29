import glob
import os
from datetime import datetime

import click
import yaml
from pydantic import BaseModel

from ted.types import Properties, TodoData, ProjectData, Reference, Task


def find_files(dir):
    files = glob.glob(os.path.join(dir, "[A-Z][0-9]*.md"))
    files.sort()
    return files


def str2todo(todo_str: str):
    t = todo_str[6:].strip()
    b = todo_str.startswith("- [x] ")
    return Task(done=b, description=t)


def new_timestamp():
    return datetime.now().strftime("%m-%d-%Y_%H:%M:%S")


def parse_project_id(proj_str: str | None) -> str | None:
    if proj_str is None:
        return None
    proj_str = proj_str.strip()
    proj_str = proj_str.replace("[[", "").replace("]]", "")
    return proj_str


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


def ref_from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()

    parts = text.split("# ")

    if parts[0] != "":
        properties = yaml.safe_load(parts[0].split("---\n")[1])
    else:
        raise ValueError("Invalid todo file format: missing properties section.")
    if "project_id" in properties:
        properties["project_id"] = parse_project_id(properties.get("project_id"))

    if "blocked_by" in properties and properties["blocked_by"] is not None:
        properties["blocked_by"] = [
            parse_project_id(item) for item in properties["blocked_by"]
        ]
    name, ref = parts[1].split("\n")[:2]
    task = parts[2].split("\n")[1].strip()

    task_id = parse_project_id(task)
    if task_id is None:
        raise ValueError("Invalid reference file format: missing task reference.")

    properties = Properties(**properties)
    filename = os.path.basename(filename)
    return Reference(
        name=name,
        ref=ref.strip(),
        properties=properties,
        filename=filename,
        task=task_id,
    )


def from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()

    parts = text.split("# ")

    if parts[0] != "":
        properties = yaml.safe_load(parts[0].split("---\n")[1])
    else:
        raise ValueError("Invalid todo file format: missing properties section.")

    properties["project_id"] = parse_project_id(properties.get("project_id"))

    if "blocked_by" in properties and properties["blocked_by"] is not None:
        properties["blocked_by"] = [
            parse_project_id(item) for item in properties["blocked_by"]
        ]
    name, goal = parts[1].split("\n")[:2]

    tasks = [str2todo(p) for p in parts[2].split("\n") if p.startswith("- [")]

    if len(parts) < 4:
        info = []
    else:
        info = [p[2:] for p in parts[3].split("\n") if p.startswith("- ")]

    properties = Properties(**properties)
    filename = os.path.basename(filename)
    return TodoData(
        name=name,
        goal=goal.strip(),
        tasks=tasks,
        properties=properties,
        info=info,
        filename=filename,
    )


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


def prompt_todo_selection(todo_dir: str):
    todo_files = find_files(todo_dir)
    if todo_files:
        click.echo("Available todo files: ")
        for i, tf in enumerate(todo_files):
            click.echo(f"{i}. {os.path.basename(tf)}")
        todo_idx = click.prompt(
            "Todo ID (leave empty for none)", default="", show_default=False
        ).strip()
    else:
        todo_idx = ""

    if todo_idx != "":
        try:
            todo_idx = int(todo_idx)
            todo_file = todo_files[todo_idx]
            todo = from_md_file(todo_file)
            todo_id = todo.id
        except (ValueError, IndexError):
            click.echo("Invalid todo selection. Proceeding without a todo.")
            todo_id = None
            todo = None
            todo_file = None
    else:
        todo_id = None
        todo = None
        todo_file = None
    return todo_id, todo, todo_file


def get_next_id(file_dir: str) -> int:
    files = find_files(file_dir)
    last_id = max([int(os.path.basename(f)[1:6]) for f in files], default=0)
    return last_id + 1
