import os


class Config:
    VAULT_DIR = os.path.expanduser("~/.ted")
    TODO_DIR = os.path.join(VAULT_DIR, "todos")
    REF_DIR = os.path.join(VAULT_DIR, "ref")
    DONE_DIR = os.path.join(VAULT_DIR, "done")
    PROJECTS_DIR = os.path.join(VAULT_DIR, "projects")
    FILES_DIR = os.path.join(VAULT_DIR, "files")
    INBOX_DIR = os.path.join(VAULT_DIR, "inbox")

    @staticmethod
    def init():
        os.makedirs(Config.TODO_DIR, exist_ok=True)
        os.makedirs(Config.DONE_DIR, exist_ok=True)
        os.makedirs(Config.PROJECTS_DIR, exist_ok=True)
        os.makedirs(Config.REF_DIR, exist_ok=True)
        os.makedirs(Config.FILES_DIR, exist_ok=True)
        os.makedirs(Config.INBOX_DIR, exist_ok=True)

