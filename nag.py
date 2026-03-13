#!/usr/bin/env python3

import sys
import os
import uuid
import datetime
import json
import shutil

"""

Filters

"status:open"
"status:orphaned"
"priority:high"
"tag:codegen"
"source:codegen.ml"
"blocked" (if depends_on is not empty and at least one dependency is not resolved)

"""

DEBUG = True

IGNORED_DIRS = {".git", "todo", "_build", "_opam"}

HELP_MESSAGE = """Usage: nag [args...]

Commands:
  new       nag "<title>" new
  tag       nag ... "<tag>" tag
  priority  nag ... <low|medium|high> priority
  save      nag ... save
  help      nag help
"""

meta = {
    "id": "",
    "title": "",
    "status": "open",
    "priority": "low",
    "notes": [],
    "attachments": [],
    "tags": [],
    "created_at": "",
    "source": "",
    "depends": [],
    "blocks": [],
}


class Nag:
    def __init__(self):
        self.s = []
        self.root = ""
        self.t = {
            "new": self.new,
            "save": self.save,
            "tag": self.tag,
            "priority": self.priority,
            "help": self.help,
            "init": self.init,
            "note": self.note,
            "attach": self.attach,
            "status": self.status,
            "ls": self.ls,
        }
        # TODO: check if ID already exists
        meta["id"] = str(uuid.uuid4())[:4]

    def init(self):
        """Initializes the Nag tool"""
        # TODO: warn if a parent nag project already exists
        path = os.path.join(os.getcwd(), "todo")
        if os.path.exists(path):
            print("already a nag project")
            exit(1)
        os.makedirs(path)
        print("initialized nag project")

    def help(self):
        """Print help message

        nag help
        """
        if len(self.s) != 0:
            print("call help with no args")
            exit(1)
        print(HELP_MESSAGE)
        exit(0)

    def ls(self):
        """List all issue IDs

        nag ls
        """
        count = 0
        for id in os.listdir(self.root + "/todo"):
            count += 1
            print(id)
        print(f"{count} issue{'s' if count != 1 else ''}")
        if count == 0:
            print("no issues")

    def status(self):
        """Set the status of the current issue

        nag "open" status save
        """
        status = self.s.pop()

        if status not in ["open", "resolved"]:
            print("status must be open or resolved")
            exit(1)
        meta["status"] = status

    def attach(self):
        """Add an attachment to the current issue

        nag "assets/crash.png" attach save
        """
        # TODO: Append attachments to existing attachments (fetch)
        attachment = self.s.pop()
        if not isinstance(attachment, str):
            print("attachment must be str")
            exit(1)
        meta["attachments"].append(attachment)

    def note(self):
        """Add a note to the current issue

        nag "see the dump for the failure case" note save
        """
        # TODO: Append notes to existing notes (fetch)
        note = self.s.pop()
        if not isinstance(note, str):
            print("note must be str")
            exit(1)
        meta["notes"].append(note)

        if DEBUG:
            print("notes:", meta["notes"])

    def find_root(self):
        """Walk up from current dir to find todo"""
        path = os.path.abspath(os.getcwd())
        while True:
            if os.path.isdir(os.path.join(path, "todo")):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent

    def tag(self):
        """Add a tag to the current issue

        nag "fix the lexer" new "codegen" tag
        """
        while True:
            if len(self.s) == 0:
                print("call tag with no args")
                exit(1)
            tag = self.s.pop()
            if not isinstance(tag, str):
                print("tag must be str")
                exit(1)
            if tag not in meta["tags"]:
                meta["tags"].append(tag)
            if len(self.s) == 0 or self.s[0] != "tag":
                break

        if DEBUG:
            print("tags:", meta["tags"])

    def priority(self):
        """Set the priority of the current issue

        nag "fix the lexer" new "high" priority
        """
        p = self.s.pop()

        if p not in ["low", "medium", "high"]:
            print("priority must be low, medium, or high")
            exit(1)
        meta["priority"] = p

        if DEBUG:
            print("priority:", meta["priority"])

    def new(self):
        """Create a new issue

        nag "fix the lexer" new
        """
        title = self.s.pop()
        if not isinstance(title, str):
            print("title must be str")
            exit(1)
        meta["title"] = title
        meta["status"] = "open"

        if DEBUG:
            print("title:", meta["title"])

    def save(self):
        """Save current issue

        nag "fix the lexer" new save
        """
        path = self.root + "/todo/" + meta["id"]
        if not os.path.exists(path):
            os.makedirs(path)

        meta["created_at"] = str(datetime.datetime.now())
        meta["updated_at"] = str(datetime.datetime.now())

        with open(path + "/meta.json", "w") as f:
            f.write(json.dumps(meta))

        body_path = path + "/body.md"
        if not os.path.exists(body_path):
            with open(body_path, "w") as f:
                for note in meta["notes"]:
                    f.write(note + "\n")

        attachments_path = path + "/attachments"
        if not os.path.exists(attachments_path):
            os.makedirs(attachments_path)

        for attachment in meta["attachments"]:
            shutil.copy(attachment, attachments_path)
            print("copied", attachment)

        print("saved issue")
        exit(0)


if __name__ == "__main__":
    n = Nag()
    if len(sys.argv) == 1:
        print(HELP_MESSAGE)
        exit(0)
    else:
        tokens = sys.argv[1:]

        needs_root = not any(token in ["init", "help"] for token in tokens)
        if needs_root:
            root = n.find_root()
            if root is None:
                print("not a nag project")
                exit(1)
            n.root = root

        for token in tokens:
            if token in n.t:
                n.t[token]()
            else:
                n.s.append(token)

        if n.s:
            print("unknown command:", *n.s)
            exit(1)
