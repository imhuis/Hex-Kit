# Hex-Kit

**AI Coding Assistant**

**Cast smarter spells. Code the bits.**

## Initialize a monorepo with shared constraints

Requires Git and Python 3.10+. Run these steps in the target project:

```bash
# 1. Initialize the repository
git init

# 2. Add Hex-Kit as a submodule
git submodule add --name .agent-spec https://github.com/imhuis/Hex-Kit.git .agent-spec

# 3. Initialize shared constraints
python .agent-spec/scripts/init-project.py
```

Use `py -3` on Windows or `python3` on macOS / Linux if needed.

The script updates the target's `AGENTS.md` to read constraints from `.agent-spec`,
preserving existing instructions. Repeat runs are supported; no commit is created.

When cloning or initializing an existing checkout:

```bash
git clone --recurse-submodules <project-url>
# For an existing checkout:
git submodule update --init --recursive -- .agent-spec
```
