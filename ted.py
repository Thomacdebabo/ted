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
    id: str
    name: str
    goal: str
    tasks: list[tuple[bool, str]]
    properties: dict = {}

    def __str__(self) -> str:
        _str = ""
        if self.properties:
            _str += properties2md(self.properties)
        _str += string2md(self.name, self.goal)
        _str += tasks2md("tasks", self.tasks)
        return _str

    @property
    def filename(self):
        return f"{self.id}_{self.name[:10].replace(' ', '_')}.md"

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w") as f:
            f.write(self.__str__())


def from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()

    parts = text.split("# ")
    if parts[0] != "":
        properties = yaml.safe_load(parts[0].split("---\n")[1])
    else:
        properties = {}
    name, goal = parts[1].split("\n")[:2]

    tasks = [str2todo(p) for p in parts[2].split("\n") if p.startswith("- [")]
    return TodoData(
        id=filename[:4], name=name, goal=goal, tasks=tasks, properties=properties
    )


VAULT_DIR = os.path.expanduser("~/.ted")


def cli():
    """TED - the todo buddy"""
    name = click.prompt("Enter the new name", type=str)
    goal = click.prompt("Enter passing criteria", type=str)
    next = click.prompt("Next task to do", type=str)

    creation_timestamp = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
    properties = {"created": creation_timestamp}

    files = find_files(VAULT_DIR)
    n_files = len(files)
    id = f"T{n_files:05d}"

    todo = TodoData(
        id=id, name=name, goal=goal, tasks=[(False, next)], properties=properties
    )
    todo.write(VAULT_DIR)


def find_files(dir):
    return glob.glob(os.path.join(dir, "T[0-9]*.md"))


if __name__ == "__main__":
    cli()
