import glob
import os
from datetime import datetime

import click
import yaml
from pydantic import BaseModel
from enum import Enum


def new_timestamp():
    return datetime.now().strftime("%m-%d-%Y_%H:%M:%S")


def properties2md(props: dict):
    return f"---\n{yaml.dump(props)}---\n"


def string2md(key: str, string: str):
    return f"# {key.capitalize()}\n{string}\n"


def list2md(key: str, lst: list[str]):
    item_string = "\n".join([f"- {item}" for item in lst])
    return f"# {key.capitalize()} \n{item_string}\n"


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
    blocked_by: list[str] | None = None

    def __str__(self):
        props = {
            "created": self.created,
            "id": self.id,
            "completed": self.completed,
            "project_id": f"[[{self.project_id}]]" if self.project_id else None,
            "tags": self.tags,
        }
        if self.blocked_by is not None:
            props["blocked_by"] = [f"[[{item}]]" for item in self.blocked_by]
        props.update(self.others)
        return f"---\n{yaml.dump(props)}---\n"


class ReferenceType(str, Enum):
    LINK = "l"
    NOTEBOOK = "n"
    FILE = "f"


def create_reference(type: ReferenceType, content: str) -> "Reference":
    if type == ReferenceType.LINK:
        if not content.startswith("http"):
            content = "https://" + content

    return Reference(type=type, content=content)


class Reference(BaseModel):
    type: ReferenceType
    content: str

    def __str__(self) -> str:
        if self.type == ReferenceType.LINK:
            return f"[link]({self.content})"
        if self.type == ReferenceType.NOTEBOOK:
            return f"Notebook: {self.content}"
        if self.type == ReferenceType.FILE:
            return f"File: [[{self.content}]]"
        else:
            return self.content


class ReferenceData(BaseModel):
    properties: Properties
    ref: Reference
    task: str
    filename: str
    name: str = "Reference"
    tldr: str = ""

    def __str__(self) -> str:
        _str = ""
        _str += str(self.properties)
        _str += string2md(self.name, str(self.ref))
        _str += string2md("Task", f"[[{self.task}]]")
        _str += string2md("TLDR", self.tldr)
        return _str

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf-8") as f:
            f.write(str(self))


class TodoData(BaseModel):
    name: str
    goal: str
    filename: str
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
    def id(self):
        return self.properties.id

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf-8") as f:
            f.write(str(self))

    def status(self) -> str:
        status = "✅" if all([t.done for t in self.tasks]) else "❌"
        status_string = f"{self.id}: {self.name} {status}\n"
        for i, t in enumerate(self.tasks):
            status_string += f" {i}. " + t.status() + "\n"
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

        timestamp = new_timestamp()
        desc = self.tasks[task_index].description
        self.add_info(f"{timestamp} | Completed: {desc}")


class ProjectData(BaseModel):
    id: str
    name: str
    properties: Properties
    filename: str
    description: str = ""
    info: list[str] = []

    def __str__(self) -> str:
        _str = ""
        _str += str(self.properties)
        _str += string2md(self.name, self.description)
        _str += list2md("info", self.info)
        return _str

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf8") as f:
            f.write(self.__str__())
