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


def todo2md(todo: tuple[bool, str]):
    if todo[0]:
        return f"- [x] {todo[1]}"
    else:
        return f"- [ ] {todo[1]}"


def str2todo(todo_str: str):
    t = todo_str[5:]
    b = todo_str.startswith("- [x] ")
    return (b, t)


def tasks2md(key: str, lst: list[tuple[bool, str]]):
    task_string = "\n".join([todo2md(l) for l in lst])
    return f"# {key.capitalize()} \n{task_string}\n"


class TodoData(BaseModel):
    _id: str
    name: str
    goal: str
    tasks: list[tuple[bool, str]]
    properties: dict = {}
    info: list[str] = []

    def __str__(self) -> str:
        _str = ""
        if self.properties:
            _str += properties2md(self.properties)
        _str += string2md(self.name, self.goal)
        _str += tasks2md("tasks", self.tasks)
        _str += list2md("info", self.info)
        return _str

    @property
    def filename(self):
        return f"{self._id}_{self.name[:15].replace(' ', '_')}.md"

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        self.properties["id"] = self._id
        with open(file_dir, "w", encoding="utf8") as f:
            f.write(self.__str__())


def from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()
    _id = os.path.basename(filename)[:6]
    parts = text.split("# ")
    if parts[0] != "":
        properties = yaml.safe_load(parts[0].split("---\n")[1])
    else:
        properties = {}
    name, goal = parts[1].split("\n")[:2]

    tasks = [str2todo(p) for p in parts[2].split("\n") if p.startswith("- [")]

    if len(parts) < 4:
        info = []
    else:
        info = [p[2:] for p in parts[3].split("\n") if p.startswith("- ")]
    return TodoData(
        _id=_id,
        name=name,
        goal=goal,
        tasks=tasks,
        properties=properties,
        info=info,
    )


VAULT_DIR = os.path.expanduser("~/.ted")
TODO_DIR = os.path.join(VAULT_DIR, "todos")
DONE_DIR = os.path.join(VAULT_DIR, "done")
os.makedirs(TODO_DIR, exist_ok=True)
os.makedirs(DONE_DIR, exist_ok=True)


@click.group()
def cli():
    """TED - the todo buddy"""
    pass


@cli.command()
def new():
    name = click.prompt("Enter the new name", type=str)
    goal = click.prompt("Enter passing criteria", type=str)
    next = click.prompt("Next task to do", type=str)

    creation_timestamp = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")

    files = find_files(TODO_DIR)
    last_id = max([int(os.path.basename(f)[1:6]) for f in files], default=0)
    n_files = last_id + 1
    _id = f"T{n_files:05d}"
    properties = {"created": creation_timestamp, "id": _id}
    todo = TodoData(
        _id=_id, name=name, goal=goal, tasks=[(False, next)], properties=properties
    )
    todo.write(TODO_DIR)


@cli.command()
@click.option("-s", "--show", is_flag=True, help="Show details for each todo")
def ls(show):
    files = find_files(TODO_DIR)
    for file in files:
        try:
            todo = from_md_file(file)
            status = "✅" if all([t[0] for t in todo.tasks]) else "❌"
            click.echo(f"{todo._id}: {todo.name} {status}")
            if show:
                click.echo(str(todo))
        except Exception as e:
            click.echo(f"Error reading {file}: {e}")


@cli.command()
@click.argument("todo_id")
def done(todo_id):
    files = find_files(TODO_DIR)
    target_file = None
    for file in files:
        if os.path.basename(file).startswith(todo_id):
            target_file = file
            break

    if not target_file:
        click.echo(f"Todo with ID {todo_id} not found.")
        return
    else:
        click.echo(f"Found todo file: {target_file}")
    todo = from_md_file(target_file)
    print(todo)
    if not all([t[0] for t in todo.tasks]):
        click.echo(f"Todo {todo_id} is not yet complete.")
        return
    todo.properties["completed"] = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
    todo.write(DONE_DIR)
    os.remove(target_file)
    click.echo(f"Todo {todo_id} marked as done and moved to done directory.")


# def update():
def find_files(dir):
    return glob.glob(os.path.join(dir, "T[0-9]*.md"))


if __name__ == "__main__":
    cli()
