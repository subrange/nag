#!/usr/bin/env python3

import sys
import os
import re
import uuid
import datetime
import json
import shutil
import copy

DEBUG = False

IGNORED_DIRS = {".git", "todo", "_build", "_opam", ".venv"}

LANGUAGES = {
    ".ml": {"block_end": "*)"},
    ".mly": {"block_end": "*)"},
    ".py": {},
    ".rs": {},
    ".c": {},
    ".h": {},
    ".js": {},
}

TODO_BARE = re.compile(r"TODO" + r":\s*(.*)")  # concat to avoid matching
TODO_BARE_META = re.compile(r"TODO" + r"<([^>]+)>:\s*(.*)")
TODO_TAGGED = re.compile(r"TODO" + r"\(([^)]+)\):\s*(.*)")
TODO_TAGGED_META = re.compile(r"TODO" + r"\(([^)]+)\)<([^>]+)>:\s*(.*)")

PRIORITIES = {"low", "medium", "high"}


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
  clear     nag "<id>" fetch clear
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
            "clear": self.clear,
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
        for id, meta in issues.items():
            for dep in meta.get("depends", []):
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
        if len(self.s) != 0:
            print("call sync with no args")
            exit(1)

        source_ids = set()
        for filepath, lang_info in self._scan_files():
            self._process_file(filepath, lang_info, source_ids)

        issues_dir = os.path.join(self.root, "todo")
        for issue_id in os.listdir(issues_dir):
            if issue_id in source_ids:
                continue
            meta_path = os.path.join(issues_dir, issue_id, "meta.json")
            if not os.path.isfile(meta_path):
                continue

            with open(meta_path, "r") as f:
                m = json.load(f)

            if m.get("status") != "orphaned":
                m["status"] = "orphaned"
                m["updated_at"] = str(datetime.datetime.now())
                with open(meta_path, "w") as f:
                    f.write(json.dumps(m))
                print(f"orphaned TODO({issue_id}): {m['title']}")

    def _parse_meta(self, meta_str):
        parts = [p.strip() for p in meta_str.split(",") if p.strip()]
        priority = next((p for p in parts if p in PRIORITIES), None)
        tags = [p for p in parts if p not in PRIORITIES]
        return priority, tags

    def _match_todo(self, line):
        """Match a TODO comment in a line.

        Returns (match, meta_str, priority, tags, title_raw, old_token) or None.
        Already-tagged TODOs return (None, existing_id, None, [], "", "").
        """
        m = TODO_TAGGED_META.search(line)
        if m:
            return None, m.group(1), None, [], "", ""

        m = TODO_TAGGED.search(line)
        if m:
            return None, m.group(1), None, [], "", ""

        m = TODO_BARE_META.search(line)
        if m:
            meta_str = m.group(1)
            priority, tags = self._parse_meta(meta_str)
            return m, meta_str, priority, tags, m.group(2), "TODO" + f"<{meta_str}>:"

        m = TODO_BARE.search(line)
        if m:
            return m, None, None, [], m.group(1), "TODO" + ":"

        return None

    def _clean_title(self, title, match, line, block_end):
        """Strip string-literal quotes and block-comment endings from a title."""
        start = match.start()
        if start > 0 and line[start - 1] == '"' and '"' in title:
            title = title[: title.index('"')].strip()

        if block_end and block_end in title:
            title = title[: title.index(block_end)].strip()

        return title

    def _collect_block_body(self, lines, start, block_end):
        """Collect continuation lines from a block comment until block_end."""
        extra = []
        j = start
        while j < len(lines):
            if block_end in lines[j]:
                content = lines[j].split(block_end)[0].strip()
                if content:
                    extra.append(content)
                break
            extra.append(lines[j].rstrip())
            j += 1
        return extra

    def _scan_files(self):
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for filename in filenames:
                ext = os.path.splitext(filename)[1]
                if ext in LANGUAGES:
                    yield os.path.join(dirpath, filename), LANGUAGES[ext]

    def _process_file(self, filepath, lang_info, source_ids):
        with open(filepath, "r", errors="replace") as f:
            lines = f.readlines()

        block_end = lang_info.get("block_end")
        modified = False
        i = 0

        while i < len(lines):
            result = self._match_todo(lines[i])
            if result is None:
                i += 1
                continue

            m, meta_str, priority, tags, title_raw, old_token = result
            if m is None:
                source_ids.add(meta_str)
                i += 1
                continue
            title = self._clean_title(title_raw.strip(), m, lines[i], block_end)

            extra_lines = []
            if block_end and block_end not in title_raw and block_end not in lines[i]:
                extra_lines = self._collect_block_body(lines, i + 1, block_end)

            new_id = str(uuid.uuid4())[:4]
            new_token = (
                f"TODO({new_id})<{meta_str}>:" if meta_str else f"TODO({new_id}):"
            )
            lines[i] = lines[i].replace(old_token, new_token, 1)
            source_ids.add(new_id)
            modified = True

            rel_path = os.path.relpath(filepath, self.root)
            self._create_issue_from_sync(
                new_id,
                title,
                extra_lines,
                f"{rel_path}:{i + 1}",
                priority=priority,
                tags=tags,
            )
            print(f"created TODO({new_id}): {title}")

            i += 1

        if modified:
            with open(filepath, "w") as f:
                f.writelines(lines)

    def _create_issue_from_sync(
        self, issue_id, title, extra_lines, source, priority=None, tags=None
    ):
        issue_dir = os.path.join(self.root, "todo", issue_id)
        if os.path.exists(issue_dir):
            return

        os.makedirs(issue_dir)
        os.makedirs(os.path.join(issue_dir, "attachments"))

        now = str(datetime.datetime.now())
        m = {
            "id": issue_id,
            "title": title,
            "status": "open",
            "priority": priority or "low",
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
            "source": source,
            "depends": [],
            "blocks": [],
        }
        with open(os.path.join(issue_dir, "meta.json"), "w") as f:
            f.write(json.dumps(m))

        body = "\n".join(extra_lines)
        with open(os.path.join(issue_dir, "body.md"), "w") as f:
            f.write(body)

    def close(self):
        """Set status to resolved and save

        nag "<id>" fetch close
        nag "fix the lexer" new close
        """
        if not self.m:
            self.m = {self.meta["id"]: self.meta}

        now = str(datetime.datetime.now())

        for id, meta in self.m.items():
            meta["status"] = "resolved"
            meta["updated_at"] = now
            if not meta.get("created_at"):
                meta["created_at"] = now

            if DEBUG:
                print(f"id: {id}")
                print(f"status: {meta['status']}")
                print(f"updated_at: {meta['updated_at']}")

            path = self.root + "/todo/" + id
            if not os.path.exists(path):
                os.makedirs(path)

            with open(path + "/meta.json", "w") as f:
                f.write(json.dumps(meta))

        count = len(self.m)
        print(f"closed {count} issue{'s' if count != 1 else ''}")

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

    def ls(self):
        """List all issue IDs

        nag ls
        """
        entries = os.listdir(self.root + "/todo")
        for id in entries:
            print(id)

        if not entries:
            print("no todos")
        else:
            print(f"{len(entries)} todo{'s' if len(entries) != 1 else ''}")

    def status(self):
        """Set the status of the current issue

        nag "open" status save
        """
        if len(self.s) == 0:
            print("call status with no args")
            exit(1)

        status = self.s.pop()

        if status not in ["open", "resolved"]:
            print("status must be open or resolved")
            exit(1)

        self.meta["status"] = status

    def attach(self):
        """Add an attachment to the current issue

        nag "assets/crash.png" attach save
        """
        if len(self.s) == 0:
            print("call attach with no args")
            exit(1)

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
        if len(self.s) == 0:
            print("call note with no args")
            exit(1)

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
        if len(self.s) == 0:
            print("call priority with no args")
            exit(1)

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
        if len(self.s) == 0:
            print("call new with no args")
            exit(1)

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

    def clear(self):
        """Remove TODO IDs from source files and delete issues

        nag "<id>" fetch clear
        nag all clear
        """
        if not self.m:
            print("no issues loaded")
            exit(1)

        for issue_id, meta in self.m.items():
            source = meta.get("source", "")
            if source:
                filepath, _, lineno = source.rpartition(":")
                filepath = os.path.join(self.root, filepath)

                if os.path.isfile(filepath) and lineno.isdigit():
                    with open(filepath, "r") as f:
                        lines = f.readlines()

                    idx = int(lineno) - 1
                    line = lines[idx] if 0 <= idx < len(lines) else ""
                    m = TODO_TAGGED_META.search(line)
                    if m and m.group(1) == issue_id:
                        old = "TODO" + f"({issue_id})<{m.group(2)}>:"
                        repl = "TODO" + f"<{m.group(2)}>:"
                    elif ("TODO" + f"({issue_id}):") in line:
                        old = "TODO" + f"({issue_id}):"
                        repl = "TODO" + ":"
                    else:
                        old = None
                        repl = ""

                    if old:
                        lines[idx] = line.replace(old, repl, 1)
                        with open(filepath, "w") as f:
                            f.writelines(lines)

            issue_dir = os.path.join(self.root, "todo", issue_id)
            if os.path.exists(issue_dir):
                shutil.rmtree(issue_dir)

            print(f"cleared TODO({issue_id}): {meta.get('title', '')}")


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
