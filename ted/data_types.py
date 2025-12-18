import os
from datetime import datetime

import yaml
from pydantic import BaseModel
from enum import Enum

from ted.config import Config


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


def id_to_int(id_str: str) -> int:
    return int("".join(c for c in id_str if c.isdigit()))


def inbox_from_md(file_content: str):
    lines = file_content.splitlines()
    if lines[0].strip() != "---":
        raise ValueError("Invalid inbox item format")

    metadata = {}
    content_lines = []
    in_metadata = True

    for line in lines[1:]:
        if in_metadata:
            if line.strip() == "---":
                in_metadata = False
            else:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        else:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()

    photo_value = metadata.get("photo", None)
    if photo_value:
        photo_value = photo_value.replace("[[", "").replace("]]", "").replace('"', "")
        metadata["photo"] = photo_value

    file_value = metadata.get("file", None)
    if file_value:
        file_value = file_value.replace("[[", "").replace("]]", "").replace('"', "")
        metadata["file"] = file_value

    return InboxItem(
        content=content,
        timestamp=metadata.get("timestamp", ""),
        id=metadata.get("id", ""),
        photo=metadata.get("photo", None),
        file=metadata.get("file", None),
    )


class InboxItem(BaseModel):
    content: str
    timestamp: str
    id: str
    photo: str | None = None
    file: str | None = None

    def __str__(self):
        photo_str = 'photo: "[[' + self.photo + ']]"\n' if self.photo else ""
        file_str = 'file: "[[' + self.file + ']]"\n' if self.file else ""
        return f"""---
timestamp: {self.timestamp}
id: {self.id}
{photo_str}{file_str}---
{self.content}

"""


class Task(BaseModel):
    done: bool
    description: str

    def to_md(self) -> str:
        if self.done:
            return f"- [x] {self.description}"
        else:
            return f"- [ ] {self.description}"

    @staticmethod
    def from_md(md_str: str) -> "Task":
        done = md_str.startswith("- [x] ")
        description = md_str[6:].strip()
        return Task(done=done, description=description)

    def status(self) -> str:
        status = StatusSymbols.DONE.value if self.done else StatusSymbols.NOT_DONE.value
        return status + f" {self.description}"

    def mark_done(self):
        self.done = True

    def mark_undone(self):
        self.done = False


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

    @property
    def id(self):
        return self.properties.id


def tasks2md(key: str, lst: list[Task]):
    task_string = "\n".join([item.to_md() for item in lst])
    return f"# {key.capitalize()} \n{task_string}\n"


class TodoData(BaseModel):
    name: str
    goal: str
    filename: str
    filepath: str
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

    @property
    def tags(self) -> list[str]:
        return self.properties.tags

    def is_completed(self) -> bool:
        return all([t.done for t in self.tasks])

    def write(self, vault_dir: str):
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf-8") as f:
            f.write(str(self))

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(str(self))

    def _status(self) -> StatusSymbols:
        if self.properties.blocked_by is not None:
            for t in self.properties.blocked_by:
                if os.path.exists(os.path.join(Config.TODO_DIR, t)) is False:
                    continue
                status = from_md_file(os.path.join(Config.TODO_DIR, t))
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

    def mark_all_done(self):
        for task in self.tasks:
            if not task.done:
                task.mark_done()
        self.add_info(f"{new_timestamp()} | All tasks marked as done.")


class ProjectData(BaseModel):
    id: str
    name: str
    properties: Properties
    filename: str
    description: str = ""
    info: list[str] = []
    shorthand: str = ""

    def __str__(self) -> str:
        _str = ""
        _str += str(self.properties)
        if self.shorthand:
            name = f"{self.shorthand}: {self.name}\n"
            _str += string2md(name, self.description)
        else:
            _str += string2md(self.name, self.description)
        _str += list2md("info", self.info)
        return _str

    def write(self, vault_dir: str) -> None:
        file_dir = os.path.join(vault_dir, self.filename)
        with open(file_dir, "w", encoding="utf8") as f:
            f.write(self.__str__())


class VaultData(BaseModel):
    todos: list[TodoData] = []
    dones: list[TodoData] = []
    projects: list[ProjectData] = []
    references: list[ReferenceData] = []

    def get_ids(self) -> dict[str, list[str]]:
        ids = {
            "todos": [todo.id for todo in self.todos + self.dones],
            "projects": [proj.id for proj in self.projects],
            "references": [ref.task for ref in self.references],
        }
        return ids

    def get_next_id(self, data_type: str) -> int:
        existing_ids = self.get_ids().get(data_type, [])
        stripped_ids = [id_to_int(id) for id in existing_ids]
        next_id = max(stripped_ids, default=0) + 1
        return next_id

    def find(self, data_type: str, item_id: str):
        item_id_int = id_to_int(item_id)
        items: list = []
        if data_type == "todos":
            items = self.todos + self.dones
        elif data_type == "projects":
            items = self.projects
        elif data_type == "references":
            items = self.references
        else:
            raise ValueError(f"Unknown data type: {data_type}")

        for i in items:
            if id_to_int(i.id) == item_id_int:
                return i
        return None


def parse_project_id(proj_str: str | None) -> str | None:
    if proj_str is None:
        return None
    proj_str = proj_str.strip()
    proj_str = proj_str.replace("[[", "").replace("]]", "")
    return proj_str


def parse_properties(prop_str: str) -> Properties:
    properties = yaml.safe_load(prop_str.split("---\n")[1])
    properties["project_id"] = parse_project_id(properties.get("project_id"))

    if "blocked_by" in properties and properties["blocked_by"] is not None:
        properties["blocked_by"] = [
            parse_project_id(item) for item in properties["blocked_by"]
        ]
    return Properties(**properties)


def from_md_file(filepath: str) -> TodoData:
    with open(filepath, "r") as f:
        text = f.read()

    parts = text.split("# ")
    if parts[0] != "":
        properties = parse_properties(parts[0])
    else:
        raise ValueError("Invalid todo file format: missing properties section.")
    name, goal = parts[1].split("\n")[:2]

    tasks = [Task.from_md(p) for p in parts[2].split("\n") if p.startswith("- [")]

    if len(parts) < 4:
        info = []
    else:
        info = [p[2:] for p in parts[3].split("\n") if p.startswith("- ")]

    filename = os.path.basename(filepath)
    return TodoData(
        name=name,
        goal=goal.strip(),
        tasks=tasks,
        properties=properties,
        info=info,
        filename=filename,
        filepath=filepath,
    )


def ref_from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()

    parts = text.split("# ")

    if parts[0] != "":
        properties = parse_properties(parts[0])
    else:
        raise ValueError("Invalid reference file format: missing properties section.")

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

    filename = os.path.basename(filename)

    return ReferenceData(
        name=name,
        ref=ref_obj,
        properties=properties,
        filename=filename,
        task=task_id,
    )


def proj_from_md_file(filename: str):
    with open(filename, "r") as f:
        text = f.read()

    parts = text.split("# ")

    if parts[0] != "":
        properties = parse_properties(parts[0])
    else:
        raise ValueError("Invalid project file format: missing properties section.")

    name, description = parts[1].split("\n")[:2]
    if ":" in name:
        shorthand, name = name.split(":", 1)
        shorthand = shorthand.strip()
        name = name.strip()
    else:
        shorthand = ""
    if len(parts) < 3:
        info = []
    else:
        info = [p[2:] for p in parts[2].split("\n") if p.startswith("- ")]

    filename = os.path.basename(filename)

    return ProjectData(
        id=properties.id,
        name=name,
        shorthand=shorthand,
        description=description.strip(),
        properties=properties,
        filename=filename,
        info=info,
    )
