#!/usr/bin/env python3

import sys
import os
import uuid
import datetime
import json
import shutil
import copy

DEBUG = False

IGNORED_DIRS = {".git", "todo", "_build", "_opam"}

HELP_MESSAGE = """Usage: nag [token ...]

Commands:
  init      nag init
  new       nag "<title>" new
  tag       nag ... "<tag>" tag
  priority  nag ... <low|medium|high> priority
  status    nag ... <open|resolved> status
  note      nag ... "<text>" note
  attach    nag ... "<file>" attach
  depends   nag ... "<id>" depends
  save      nag ... save
  close     nag "<id>" fetch close
  fetch     nag "<id>" fetch
  ls        nag ls
  all       nag all
  filter    nag all "<field:value>" filter
  sort      nag all sort:<field>
  show      nag all show
  graph     nag all graph
  sync      nag sync
  help      nag help
"""

ORDINAL = {
    "priority": {"low": 0, "medium": 1, "high": 2},
    "status": {"open": 0, "resolved": 1},
}

DEFAULT_META = {
    "id": "",
    "title": "",
    "status": "open",
    "priority": "low",
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
            "all": self.all,
            "close": self.close,
            "sort": self.sort_list,
            "fetch": self.fetch,
            "filter": self.filter,
            "show": self.show,
            "graph": self.graph,
            "depends": self.depends,
            "sync": self.sync,
        }
        self.m = {}
        self._reset_meta()

    def _generate_id(self):
        """Generate a unique 4-char issue ID"""
        while True:
            candidate = str(uuid.uuid4())[:4]
            if not self.root or not os.path.exists(self.root + "/todo/" + candidate):
                return candidate

    def _reset_meta(self):
        self.meta = copy.deepcopy(DEFAULT_META)
        self.meta["id"] = self._generate_id()
        self.notes = []
        self.attachments = []

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

    def sort_list(self):
        """Sort loaded issues by a field name

        Expects a field name string on the stack (e.g. "priority", "created_at").
        Requires `all` first.

        nag all sort:priority show
        """
        if len(self.s) == 0:
            print("call sort with no args")
            exit(1)

        field = self.s.pop()

        if not isinstance(field, str):
            print("field must be str")
            exit(1)

        if field not in DEFAULT_META:
            print(f"unknown sort field: {field}")
            exit(1)

        order = ORDINAL.get(field, {})

        def sort_key(item):
            value = item[1][field]
            return order[value] if value in order else value

        self.m = dict(sorted(self.m.items(), key=sort_key))

        if DEBUG:
            print("sorted:", self.m)

    def fetch(self):
        """Load a single issue by ID

        nag "x91b" fetch show
        """
        if len(self.s) == 0:
            print("call fetch with no args")
            exit(1)

        id = self.s.pop()

        if not isinstance(id, str):
            print("id must be str")
            exit(1)

        path = self.root + "/todo/" + id
        if not os.path.exists(path):
            print(f"todo not found: {id}")
            exit(1)

        with open(path + "/meta.json") as f:
            self.meta = json.load(f)

        body_path = path + "/body.md"
        if os.path.exists(body_path):
            with open(body_path) as f:
                self.notes = [line.rstrip("\n") for line in f if line.strip()]

        self.m = {id: self.meta}

        if DEBUG:
            print("fetched:", self.m)

    def _filter_eq(self, field, value, valid=None):
        if valid and value not in valid:
            print(f"{field} must be one of: {', '.join(valid)}")
            exit(1)
        self.m = {k: v for k, v in self.m.items() if v[field] == value}

    def _filter_contains(self, field, value):
        self.m = {k: v for k, v in self.m.items() if value in v[field]}

    def filter(self):
        """Filter loaded issues by a predicate string

        Predicate: "field:value". Requires `all` first.

        nag all "status:open" filter show
        """
        if len(self.s) == 0:
            print("call filter with no args")
            exit(1)

        predicate = self.s.pop()

        if not isinstance(predicate, str):
            print("predicate must be str")
            exit(1)

        field, sep, value = predicate.partition(":")
        if not sep:
            print("unknown predicate:", predicate)
            exit(1)

        if field == "status":
            self._filter_eq("status", value, ["open", "resolved", "orphaned"])
        elif field == "priority":
            self._filter_eq("priority", value, ["low", "medium", "high"])
        elif field == "tag":
            self._filter_contains("tags", value)
        elif field in ("source", "blocks", "depends", "title", "id"):
            self._filter_contains(field, value)
        elif field in ("created_at", "updated_at"):
            self._filter_eq(field, value)
        else:
            print("unknown predicate:", predicate)
            exit(1)

        if DEBUG:
            print("filtered:", self.m)

    def show(self):
        """Print the loaded issue list

        nag all show
        """
        # generated with ChatGPT

        def fmt_date(s):
            if not s:
                return ""
            return datetime.datetime.fromisoformat(s).strftime("%Y-%m-%d %H:%M")

        issues = list(self.m.values())
        if not issues:
            print("no todos")
            return

        col_widths = [
            max(len(m["id"]) for m in issues),
            max(len(m["title"]) for m in issues),
            max(len(m["status"]) for m in issues),
            max(len(m["priority"]) for m in issues),
            max(len(fmt_date(m["created_at"])) for m in issues),
        ]

        for meta in issues:
            extras = meta["tags"] + meta["depends"] + meta["blocks"]
            if meta["source"]:
                extras.append(meta["source"])
            parts = [
                meta["id"].ljust(col_widths[0]),
                meta["title"].ljust(col_widths[1]),
                meta["status"].ljust(col_widths[2]),
                meta["priority"].ljust(col_widths[3]),
                fmt_date(meta["created_at"]).ljust(col_widths[4]),
            ] + extras
            print("  ".join(parts).rstrip())

    def graph(self):
        """Print an ASCII dependency DAG of loaded issues

        nag all graph
        """
        issues = self.m
        if not issues:
            print("no todos")
            return

        dependents = {id: [] for id in issues}
        all_dep_ids = set()
        for id, meta in issues.items():
            for dep in meta.get("depends", []):
                all_dep_ids.add(dep)
                if dep in dependents:
                    dependents[dep].append(id)

        roots = [
            id
            for id in issues
            if not any(dep in issues for dep in issues[id].get("depends", []))
        ] or list(issues.keys())

        # Tree printing adapted from:
        # https://simonhessner.de/python-3-recursively-print-structured-tree-including-hierarchy-markers-using-depth-first-search/
        def print_tree(id, visited, level_markers=[]):
            prefix = "".join("│   " if draw else "    " for draw in level_markers[:-1])

            if level_markers:
                prefix += "├── " if level_markers[-1] else "└── "

            if id not in issues:
                print(f"{prefix}{id}  (not loaded)")
                return

            if id in visited:
                print(f"{prefix}{id}  [cycle]")
                return

            meta = issues[id]
            print(
                f"{prefix}{id}  {meta['title']}  [{meta['status']}, {meta['priority']}]"
            )

            children = dependents.get(id, [])
            for i, child in enumerate(children):
                print_tree(
                    child, visited | {id}, [*level_markers, i < len(children) - 1]
                )

        for root_id in roots:
            print_tree(root_id, set())

    def depends(self):
        """Add a dependency to the current issue

        nag "x91b" fetch "y22c" depends save
        """
        if len(self.s) == 0:
            print("call depends with no args")
            exit(1)

        id = self.s.pop()

        if not isinstance(id, str):
            print("id must be str")
            exit(1)

        if id not in self.meta["depends"]:
            self.meta["depends"].append(id)

        if DEBUG:
            print("depends:", self.meta["depends"])

    def sync(self):
        """Scan source files, assign IDs to comments, and detect orphans

        nag sync
        """
        pass

    def ls(self):
        """List all issue IDs

        nag ls
        """
        count = 0

        for id in os.listdir(self.root + "/todo"):
            count += 1
            print(id)

        if count == 0:
            print("no todos")
        else:
            print(f"{count} todo{'s' if count != 1 else ''}")

    def close(self):
        """Set status to resolved and save

        nag "fix the lexer" new close
        """
        # TODO: update fetched issues
        if len(self.s) == 0:
            print("call close with no args")
            exit(1)

        id = self.s.pop()

        if not isinstance(id, str):
            print("id must be str")
            exit(1)

        self.meta["status"] = "resolved"
        self.meta["updated_at"] = str(datetime.datetime.now())

        with open(self.root + "/todo/" + id + "/meta.json", "w") as f:
            f.write(json.dumps(self.meta))

        print("closed issue")

    def all(self):
        """Load all issue objects

        nag all "status:open" filter "priority:high" filter show
        """
        for id in os.listdir(self.root + "/todo"):
            path = self.root + "/todo/" + id
            with open(path + "/meta.json") as f:
                meta = json.load(f)
                self.m[id] = meta
                if DEBUG:
                    print(meta)

    def status(self):
        """Set the status of the current issue

        nag "open" status save
        """
        status = self.s.pop()

        if status not in ["open", "resolved"]:
            print("status must be open or resolved")
            exit(1)
        self.meta["status"] = status

    def attach(self):
        """Add an attachment to the current issue

        nag "assets/crash.png" attach save
        """
        attachment = self.s.pop()
        if not isinstance(attachment, str):
            print("attachment must be str")
            exit(1)

        if not os.path.exists(attachment):
            print(f"attachment not found: {attachment}")
            exit(1)

        self.attachments.append(attachment)

    def note(self):
        """Add a note to the current issue

        nag "see the dump for the failure case" note save
        """
        note = self.s.pop()

        if not isinstance(note, str):
            print("note must be str")
            exit(1)

        self.notes.append(note)

        if DEBUG:
            print("notes:", self.notes)

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

            if tag not in self.meta["tags"]:
                self.meta["tags"].append(tag)

            if len(self.s) == 0 or self.s[0] != "tag":
                break

        if DEBUG:
            print("tags:", self.meta["tags"])

    def priority(self):
        """Set the priority of the current issue

        nag "fix the lexer" new "high" priority
        """
        p = self.s.pop()

        if p not in ["low", "medium", "high"]:
            print("priority must be low, medium, or high")
            exit(1)

        self.meta["priority"] = p

        if DEBUG:
            print("priority:", self.meta["priority"])

    def new(self):
        """Create a new issue

        nag "fix the lexer" new
        """
        title = self.s.pop()

        if not isinstance(title, str):
            print("title must be str")
            exit(1)

        if not title.strip():
            print("title must not be empty")
            exit(1)

        self.meta["title"] = title
        self.meta["status"] = "open"

        if DEBUG:
            print("title:", self.meta["title"])

    def save(self):
        """Save current issue

        nag "fix the lexer" new save
        """
        path = self.root + "/todo/" + self.meta["id"]
        if not os.path.exists(path):
            os.makedirs(path)

        if not self.meta.get("created_at"):
            self.meta["created_at"] = str(datetime.datetime.now())
        self.meta["updated_at"] = str(datetime.datetime.now())

        with open(path + "/meta.json", "w") as f:
            f.write(json.dumps(self.meta))

        body_path = path + "/body.md"
        with open(body_path, "w") as f:
            for note in self.notes:
                f.write(note + "\n")

        attachments_path = path + "/attachments"
        if not os.path.exists(attachments_path):
            os.makedirs(attachments_path)

        for attachment in self.attachments:
            shutil.copy(attachment, attachments_path)
            print("copied", attachment)

        print("saved issue")


def split_pipelines(tokens):
    pipelines, current = [], []
    for token in tokens:
        parts = token.split("+")
        for i, part in enumerate(parts):
            if part:
                current.append(part)
            if i < len(parts) - 1:
                if current:
                    pipelines.append(current)
                current = []
    if current:
        pipelines.append(current)
    return pipelines


if __name__ == "__main__":
    n = Nag()
    if len(sys.argv) == 1:
        print(HELP_MESSAGE)
        exit(0)

    pipelines = split_pipelines(sys.argv[1:])

    n.root = n.find_root() or ""

    for i, pipeline in enumerate(pipelines):
        if len(pipelines) > 1:
            if i > 0:
                print()
            print(f"query {i + 1}:")

        needs_root = any(t in n.t and t not in {"init", "help"} for t in pipeline)

        if needs_root and not n.root:
            print("not a nag project")
            exit(1)

        for token in pipeline:
            if token in n.t:
                if DEBUG:
                    print("Call token:", token)
                n.t[token]()
            elif token.startswith("sort:"):
                if DEBUG:
                    print("Sort token:", token)
                n.s.append(token[len("sort:") :])
                n.t["sort"]()
            elif ":" in token and token[: token.index(":")] in DEFAULT_META:
                if DEBUG:
                    print("Append token:", token)
                n.s.append(token)
            else:
                n.s.append(token)

        if n.s:
            print("unknown command:", *n.s)
            exit(1)

        n._reset_meta()
        n.s.clear()
