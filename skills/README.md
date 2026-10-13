<!--
BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE
-->

# AI Agent skills

Agent skills for use with Knowledge Discovery (IDOL) components.

Each skill is a directory holding a `SKILL.md` and any files it references.
Nothing here depends on anything else on your machine.

## Installing them

A Claude Code agent finds skills in a `.claude/skills/` directory.
A GitHub Copilot agent finds skills in a `.github/skills/` directory.
Copy each skill directory into one:

```sh
# for one project
mkdir -p <your-project>/.claude/skills
cp -r <Component>/<Skill> <your-project>/.claude/skills/

# or for every project you work on
mkdir -p ~/.claude/skills
cp -r <Component>/<Skill> ~/.claude/skills/
```

```powershell
# for one project
New-Item -ItemType Directory -Force <your-project>\.claude\skills | Out-Null
Copy-Item -Recurse <Component>\<Skill> <your-project>\.claude\skills\

# or for every project you work on
New-Item -ItemType Directory -Force $HOME\.claude\skills | Out-Null
Copy-Item -Recurse <Component>\<Skill> $HOME\.claude\skills\
```

Start a new agent session afterwards; added skills should then be offered by name.
