import glob
import os
from datetime import datetime

import click
import yaml
from pydantic import BaseModel
from enum import Enum


from ted.config import VAULT_DIR, TODO_DIR, REF_DIR, DONE_DIR, PROJECTS_DIR, FILES_DIR


class ReferenceType(str, Enum):
    LINK = "l"
    NOTEBOOK = "n"
    FILE = "f"


class StatusSymbols(str, Enum):
    DONE = "✅"
    NOT_DONE = "❌"
    BLOCKED = "⛔"
    WARNING = "⚠️"


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
        status = StatusSymbols.DONE.value if self.done else StatusSymbols.NOT_DONE.value
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

    def is_completed(self) -> bool:
        return all([t.done for t in self.tasks])

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf-8") as f:
            f.write(str(self))

    def _status(self) -> StatusSymbols:
        if self.properties.blocked_by is not None:
            for t in self.properties.blocked_by:
                if os.path.exists(os.path.join(TODO_DIR, t)) is False:
                    continue
                status = from_md_file(os.path.join(TODO_DIR, t))
                if status._status() != StatusSymbols.DONE:
                    return StatusSymbols.BLOCKED

        if self.is_completed():
            return StatusSymbols.DONE
        else:
            return StatusSymbols.NOT_DONE

    def status(self, verbose=False) -> str:
        status = self._status().value

        status_string = f"{self.id}: {self.name} {status}"

        if not verbose:
            return status_string
        status_string += "\nTasks:\n"
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


def parse_project_id(proj_str: str | None) -> str | None:
    if proj_str is None:
        return None
    proj_str = proj_str.strip()
    proj_str = proj_str.replace("[[", "").replace("]]", "")
    return proj_str


def str2todo(todo_str: str):
    t = todo_str[6:].strip()
    b = todo_str.startswith("- [x] ")
    return Task(done=b, description=t)


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
    if ref.startswith("[link]("):
        ref_content = ref[len("[link](") : -1]
        ref_obj = Reference(type=ReferenceType.LINK, content=ref_content)
    elif ref.startswith("Notebook: "):
        ref_content = ref[len("Notebook: ") :]
        ref_obj = Reference(type=ReferenceType.NOTEBOOK, content=ref_content)
    elif ref.startswith("File: [[") and ref.endswith("]]"):
        ref_content = ref[len("File: [[") : -2]
        ref_obj = Reference(type=ReferenceType.FILE, content=ref_content)
    else:
        raise ValueError("Invalid reference file format: unknown reference type.")
    task = parts[2].split("\n")[1].strip()

    task_id = parse_project_id(task)
    if task_id is None:
        raise ValueError("Invalid reference file format: missing task reference.")

    properties = Properties(**properties)
    filename = os.path.basename(filename)
    return ReferenceData(
        name=name,
        ref=ref_obj,
        properties=properties,
        filename=filename,
        task=task_id,
    )
