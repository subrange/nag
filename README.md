# Nag

A postfix stack-based DSL for tracking todo inside a project.

> [!WARNING]
> I wouldn't recommend using this in production. I use it for my own personal projects.

```sh
nag "fix the lexer" new "high" priority save
```

The language is super basic. There are quote literals and keywords that push and pop from a stack.

## Project structure

If you run `nag init` it creates a `todo/` directory. Once you `save`, the tool creates an issue directory for each ID in your source files.

> [!NOTE]
> The tool walks up the current directory until it finds a `todo/` directory.

```
todo/
  <id>/
    meta.json     - tags, title, timestamps, etc.
    body.md       - freeform markdown
    attachments/  - anything really
```

The `meta.json` schema is:

```json
{
  "id": "x91b",
  "title": "Fix the lexer",
  "status": "open",
  "priority": "low",
  "tags": [],
  "created_at": "2026-03-12T10:00:00Z",
  "updated_at": "2026-03-12T10:00:00Z",
  "source": "compiler/lib/lexer.ml:42",
  "depends_on": [],
  "blocks": []
}
```

The IDs are short (4 hex chars) generated from UUID library. And, yes, that's enough, you have 36^4 = 1,679,616 unique IDs.

## Keywords

| Keyword    | Description                            |
| ---------- | -------------------------------------- |
| `new`      | Create a new issue object              |
| `tag`      | Add a tag                              |
| `priority` | Set priority (`low`, `medium`, `high`) |
| `save`     | Write changes to disk                  |

## Progress

These are some things that I'm working on right now:

- [ ] `ls` push all issue IDs from `todo/`
- [ ] `all` push all fully loaded issue objects
- [ ] `fetch` load a single issue by ID
- [ ] `filter` filter list by predicate string
- [ ] `sort` sort list by field name
- [ ] `show` print issue list
- [ ] `graph` print ASCII dependency DAG
- [ ] `status` set issue status
- [ ] `note` append text to `body.md`
- [ ] `attach` copy a file into `attachments/`
- [ ] `depends` add a dependency
- [ ] `close` set status to resolved and save
- [ ] `sync` scan source files, assign IDs, detect orphans

The `all` is special version of `ls` because it loads every `meta.json` off disk instead of just the ID strings. You'll nee `all` before `filter`, `sort`, or `show` since those operations need the actual field values.

## Examples

Before, I start creating any language I like writing down some examples of how I would use the tool:

Show all open high priority codegen todo:

```sh
nag all "status:open" filter "priority:high" filter "tag:codegen" filter show
```

Create a new issue with tags:

```sh
nag "fix register allocator" new "high" priority "codegen" tag save
```

Add a note and attachment to an existing issue:

```sh
nag "x91b" fetch "see the dump for the failure case" note "assets/crash.png" attach save
```

Show the dependency graph:

```sh
nag all graph
```

## References

I only watched the first couple minutes of the Compiler Query Language video but I knew exactly what I wanted to do.

Inspiration: [Compiler Query Language](https://www.youtube.com/watch?v=8NdRGmp70Go)
