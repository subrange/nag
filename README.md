![nag](docs/logo.svg)

A postfix stack-based DSL for tracking todo inside a project.

> [!WARNING]
> I wouldn't recommend using this in production. I use it for my own personal projects.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/subrange/nag/main/install.sh | sh
```

Requires `python3` and either `curl` or `wget`.

## Keywords

| Keyword        | Description                                   |
| -------------- | --------------------------------------------- |
| `init`         | Initialize a nag project                      |
| `new`          | Create a new issue object                     |
| `tag`          | Add a tag                                     |
| `priority`     | Set priority (`low`, `medium`, `high`)        |
| `status`       | Set issue status (`open`, `resolved`)         |
| `note`         | Append text to `body.md`                      |
| `attach`       | Copy a file into `attachments/`               |
| `depends`      | Add a dependency                              |
| `save`         | Write changes to disk                         |
| `close`        | Set status to resolved and save               |
| `fetch`        | Load a single issue by ID                     |
| `all`          | Load all issues                               |
| `me`           | Load issues assigned to the current user      |
| `others`       | Load issues not assigned to the current user  |
| `pick`         | Assign loaded issues to the current user      |
| `filter`       | Filter list by predicate string               |
| `sort:<field>` | Sort list by field name                       |
| `show`         | Print issue list                              |
| `graph`        | Print ASCII dependency DAG                    |
| `sync`         | Scan source files, assign IDs, detect orphans |
| `clear`        | Remove TODO IDs from source and delete issues |
| `help`         | Print help message                            |
| `+`            | Separate multiple pipelines in one command    |

## Examples

Show all open high priority codegen todo:

```sh
nag all status:open filter priority:high filter tag:codegen filter show
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
