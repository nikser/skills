# skills

Agent skills by Nikolay Efimov. Each skill lives in `skills/<name>/` with a `SKILL.md`
(YAML frontmatter `name` + `description`, then instructions) and optional `scripts/`,
`references/`, `templates/`, `assets/`.

```
skills/
  <skill-name>/
    SKILL.md
    scripts/      # optional helpers the skill calls
    references/   # optional docs loaded on demand
```

## Install

Hermes Agent:

```bash
hermes skills tap add nikser/skills
hermes skills install nikser/skills/skills/<skill-name>
```

Any other agent that reads `SKILL.md`: copy `skills/<skill-name>/` into its skills directory.

## Skills

| Skill | What it does |
|---|---|
| — | — |
