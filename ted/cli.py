import glob
import os
from datetime import datetime

import click
import yaml
from pydantic import BaseModel


def properties2md(props: dict):
    return f"---\n{yaml.dump(props)}---\n"


def string2md(key: str, string: str):
    return f"# {key.capitalize()} \n {string} \n"


def list2md(key: str, lst: list[str]):
    item_string = "\n".join([f"- {item}" for item in lst])
    return f"# {key.capitalize()} \n{item_string}\n"


def str2todo(todo_str: str):
    t = todo_str[5:]
    b = todo_str.startswith("- [x] ")
    return Task(done=b, description=t)


def find_todo_file(todo_id: str):
    files = find_files(TODO_DIR)
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


def parse_project_id(proj_str: str | None) -> str | None:
    if proj_str is None:
        return None
    proj_str = proj_str.strip()
    proj_str = proj_str.replace("[[", "").replace("]]", "")
    return proj_str


class Task(BaseModel):
    done: bool
    description: str

    def to_md(self) -> str:
        if self.done:
            return f"- [x] {self.description}"
        else:
            return f"- [ ] {self.description}"

    def status(self) -> str:
        status = "✅" if self.done else "❌"
        return status + f" {self.description}"

    def mark_done(self):
        self.done = True

    def mark_undone(self):
        self.done = False


def tasks2md(key: str, lst: list[Task]):
    task_string = "\n".join([l.to_md() for l in lst])
    return f"# {key.capitalize()} \n{task_string}\n"


class Properties(BaseModel):
    created: str
    id: str
    completed: str | None = None
    project_id: str | None = None
    tags: list[str] = []
    others: dict = {}

    def __str__(self):
        props = {
            "created": self.created,
            "id": self.id,
            "completed": self.completed,
            "project_id": f"[[{self.project_id}]]" if self.project_id else None,
            "tags": self.tags,
        }
        props.update(self.others)
        return f"---\n{yaml.dump(props)}---\n"


class TodoData(BaseModel):
    name: str
    goal: str
    tasks: list[Task] = []
    properties: Properties
    info: list[str] = []

    def __str__(self) -> str:
        _str = ""
        _str += str(self.properties)
        _str += string2md(self.name, self.goal)
        _str += tasks2md("tasks", self.tasks)
        _str += list2md("info", self.info)
        return _str

    @property
    def filename(self):
        return f"{self.id}.md"

    @property
    def id(self):
        return self.properties.id

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf8") as f:
            f.write(str(self))

    def status(self) -> str:
        status = "✅" if all([t.done for t in self.tasks]) else "❌"
        status_string = f"{self.id}: {self.name} {status}"
        for i, t in enumerate(self.tasks):
            status_string += f"\n {i}. " + t.status()
        return status_string

    def add_info(self, info_str: str):
        self.info.append(info_str)

    def add_task(self, task_desc: str):
        self.tasks.append(Task(done=False, description=task_desc))

    def mark_task_done(self, task_index: int):
        if 0 <= task_index < len(self.tasks):
            self.tasks[task_index].mark_done()
        else:
            raise IndexError("Task index out of range.")

        timestamp = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
        desc = self.tasks[task_index].description
        self.add_info(f"{timestamp} | Completed: {desc}")


class ProjectData(BaseModel):
    id: str
    name: str
    properties: Properties
    description: str = ""
    info: list[str] = []

    def __str__(self) -> str:
        _str = ""
        _str += str(self.properties)
        _str += string2md(self.name, self.description)
        _str += list2md("info", self.info)
        return _str

    @property
    def filename(self):
        return f"{self.id}.md"

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf8") as f:
            f.write(self.__str__())


def from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()

    parts = text.split("# ")

    if parts[0] != "":
        properties = yaml.safe_load(parts[0].split("---\n")[1])
    else:
        raise ValueError("Invalid todo file format: missing properties section.")
    properties["project_id"] = parse_project_id(properties.get("project_id"))
    name, goal = parts[1].split("\n")[:2]

    tasks = [str2todo(p) for p in parts[2].split("\n") if p.startswith("- [")]

    if len(parts) < 4:
        info = []
    else:
        info = [p[2:] for p in parts[3].split("\n") if p.startswith("- ")]

    properties = Properties(**properties)
    return TodoData(
        name=name,
        goal=goal,
        tasks=tasks,
        properties=properties,
        info=info,
    )


VAULT_DIR = os.path.expanduser("~/.ted")
TODO_DIR = os.path.join(VAULT_DIR, "todos")
DONE_DIR = os.path.join(VAULT_DIR, "done")
PROJECTS_DIR = os.path.join(VAULT_DIR, "projects")


def todo_id_completion(ctx, param, incomplete):
    """Return CompletionItem list of todo IDs (first 6 chars of filename)."""
    # TODO: not working yet unfortunately
    # use an absolute, expanded path to the todo folder so we don't accidentally
    # match files in the current working directory
    abs_todo_dir = os.path.abspath(os.path.expanduser(TODO_DIR))
    if not os.path.isdir(abs_todo_dir):
        return []

    pattern = os.path.join(abs_todo_dir, "T[0-9]*.md")
    files = glob.glob(pattern)
    ids = [os.path.basename(f)[:6] for f in files]
    matches = [i for i in ids if i.startswith(incomplete)]

    # Return CompletionItem instances when supported, otherwise plain strings
    try:
        return [click.shell_completion.CompletionItem(i) for i in matches]
    except Exception:
        return matches


@click.group()
def cli():
    """TED - the todo buddy"""
    pass


@cli.command()
def new():
    name = click.prompt("Enter the new name", type=str)
    goal = click.prompt("Enter passing criteria", type=str)
    next = click.prompt("Next task to do", type=str)
    project_files = find_files(PROJECTS_DIR)

    if project_files:
        click.echo("Available project files: ")
        for i, pf in enumerate(project_files):
            click.echo(f"{i}. {os.path.basename(pf)}")
        project_idx = click.prompt(
            "Project ID (leave empty for none)", default=None, show_default=False
        ).strip()
    else:
        project_idx = None

    if project_idx is not None:
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
    creation_timestamp = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")

    files = find_files(TODO_DIR)
    last_id = max([int(os.path.basename(f)[1:6]) for f in files], default=0)
    n_files = last_id + 1
    _id = f"T{n_files:05d}"

    properties = Properties(
        created=creation_timestamp,
        id=_id,
        project_id=project_id if project_id else None,
    )

    tasks = [Task(done=False, description=next)]
    todo = TodoData(id=_id, name=name, goal=goal, tasks=tasks, properties=properties)
    todo.write(TODO_DIR)


@cli.command()
def new_p():
    name = click.prompt("Enter the new project name", type=str)
    description = click.prompt("Enter project description", type=str)

    creation_timestamp = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")

    files = find_files(PROJECTS_DIR)
    last_id = max([int(os.path.basename(f)[1:6]) for f in files], default=0)
    n_files = last_id + 1
    _id = f"P{n_files:05d}"
    properties = {"created": creation_timestamp, "id": _id}

    project = ProjectData(
        id=_id, name=name, description=description, properties=properties
    )
    project.write(PROJECTS_DIR)


@cli.command()
@click.argument("todo_id", shell_complete=todo_id_completion)
def update(todo_id):
    todo_tuple = find_todo_file(todo_id)
    if not todo_tuple:
        click.echo(f"Todo with ID {todo_id} not found.")
        return
    todo, target_file = todo_tuple

    click.echo(todo.status())
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

    with open(target_file, "w", encoding="utf8") as f:
        f.write(str(todo))

    click.echo(f"Updated todo {todo.id} and wrote changes to {target_file}")


@cli.command()
@click.option("-s", "--show", is_flag=True, help="Show details for each todo")
def ls(show):
    files = find_files(TODO_DIR)
    for file in files:
        try:
            todo = from_md_file(file)
            status = "✅" if all([t.done for t in todo.tasks]) else "❌"
            click.echo(f"{todo.id}: {todo.name} {status}")
            if show:
                click.echo(str(todo))
        except Exception as e:
            click.echo(f"Error reading {file}: {e}")


@cli.command()
@click.argument("todo_id", shell_complete=todo_id_completion)
def done(todo_id):
    todo, target_file = find_todo_file(todo_id)

    if not todo:
        return

    if not all([t.done for t in todo.tasks]):
        click.echo(f"Todo {todo_id} is not yet complete.")
        return

    todo.properties.completed = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
    todo.write(DONE_DIR)

    os.remove(target_file)
    click.echo(f"Todo {todo_id} marked as done and moved to done directory.")


@cli.command()
@click.argument("todo_id", shell_complete=todo_id_completion)
def show(todo_id):
    todo_tuple = find_todo_file(todo_id)
    if not todo_tuple:
        click.echo(f"Todo with ID {todo_id} not found.")
        return
    todo, target_file = todo_tuple

    click.echo(str(todo))


@cli.command()
def init():
    """Initialize the TED vault directories."""
    os.makedirs(TODO_DIR, exist_ok=True)
    os.makedirs(DONE_DIR, exist_ok=True)
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    click.echo(f"Initialized TED vault at {VAULT_DIR}.")


def find_files(dir):
    return glob.glob(os.path.join(dir, "[A-Z][0-9]*.md"))


def main():
    cli()


if __name__ == "__main__":
    main()
