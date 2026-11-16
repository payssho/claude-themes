# Claude themes

Backgrounds and colour themes for the Claude app, each one a small plugin
with a slash command that turns it on.

| Theme | Command | |
| --- | --- | --- |
| [Night theme](night-theme/) | `/night-theme` | A pixel-art cyberpunk city at night, with a neon indigo palette. |

![Night theme](night-theme/assets/night-city.png)

## Install a theme

At the prompt of a Claude Code terminal session:

```
/plugin install night-theme --marketplace payssho/claude-themes
```

Answer `y` to add the marketplace, then pick a scope. Swap `night-theme` for
the name of any theme in the table.

From a shell:

```bash
claude plugin install night-theme --marketplace payssho/claude-themes
```

In the desktop app, where `/plugin` does not run: click **+** next to the
prompt box, then **Plugins**, **Add marketplace** with `payssho/claude-themes`,
then **Add plugin**.

Then type the theme's command, such as `/night-theme`. Backgrounds show in the
desktop and mobile apps; a terminal draws none.

## Add a theme

Each theme is a folder at the top of this repository, holding a plugin
(`.claude-plugin/plugin.json`, `hooks/`) and its pictures, and gets an entry
in `.claude-plugin/marketplace.json`.
