from ted.config import Config
import os
from ted.data_types import (
    VaultData,
    from_md_file,
    ref_from_md_file,
    proj_from_md_file,
)


class Vault:
    def __init__(self, config: Config):
        self.ROOT_DIR = config.VAULT_DIR

        if not os.path.exists(self.ROOT_DIR):
            raise Exception("Vault directory does not exist.")

        self.required_dirs = {
            "todos": config.TODO_DIR,
            "done": config.DONE_DIR,
            "projects": config.PROJECTS_DIR,
            "ref": config.REF_DIR,
            "files": config.FILES_DIR,
        }

    def get_files(self, root_dir: str, file_extension: str = ".md"):
        files: list[tuple[str, str, str]] = []

        for root, dirs, fs in os.walk(root_dir):
            for file in fs:
                if not file.endswith(file_extension):
                    continue
                rel_path = os.path.relpath(root, root_dir)
                files.append((rel_path, file, os.path.join(root, file)))

        return files

    def load_todos(self):
        todo_files = self.get_files(self.required_dirs["todos"])
        todos = []
        for dirs, file, full_path in todo_files:
            todo = from_md_file(full_path)
            todos.append((dirs, todo))
        return todos

    def load_vault_data(self) -> VaultData:
        todo_files = self.get_files(self.required_dirs["todos"])
        done_files = self.get_files(self.required_dirs["done"])
        project_files = self.get_files(self.required_dirs["projects"])
        reference_files = self.get_files(self.required_dirs["ref"])

        todos = []
        for dirs, file, full_path in todo_files:
            todo = from_md_file(full_path)
            if todo:
                todos.append(todo)
        dones = []
        for dirs, file, full_path in done_files:
            done = from_md_file(full_path)
            if done:
                dones.append(done)

        projects = []
        for dirs, file, full_path in project_files:
            project = proj_from_md_file(full_path)
            projects.append(project)

        references = []
        for dirs, file, full_path in reference_files:
            reference = ref_from_md_file(full_path)
            references.append(reference)

        return VaultData(
            todos=todos, dones=dones, projects=projects, references=references
        )

    def print_todos(self, todos):
        tmp_todos = [(dirs, todo) for dirs, todo in todos]
        tmp_todos.sort(key=lambda x: x[0])
        last_dir = ""
        for dirs, todo in tmp_todos:
            if dirs != last_dir:
                print(f"\n{'	' * (dirs.count('/'))}Directory: {dirs}")
                last_dir = dirs
            print(f"{'	' * (dirs.count('/') + 1)}{todo.id}: {todo.name}")
