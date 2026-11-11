# Lightless Group Examiner

A local dashboard for inspecting your LightlessSync syncshells in FFXIV. See which players appear in multiple groups, which players are unique to a group, and how leaving a syncshell could affect your coverage.

The analyzer runs on your computer and opens in your browser. The GitHub Pages website is the project guide; it does not run the analyzer.

## Features

- Compare group sizes, shared players, unique players, and redundancy.
- Browse syncshells in grid, list, or interactive network views.
- Search by group name or GID, filter by leave impact, and sort results.
- Open a group to inspect its overlaps and search its player list.
- Switch between characters and use the latest diagnostics report for each one.
- Resolve player and group names from local notes, configuration, and diagnostics.

## Getting started

You need Windows, Python 3 available as `python`, a browser, and an existing LightlessSync configuration. The backend uses only the Python standard library, so there are no packages to install with pip.

1. Download this repository using **Code > Download ZIP** and extract it, or clone it:

   ```powershell
   git clone https://github.com/ric6121824/LightlessGroupExaminer.git
   cd LightlessGroupExaminer
   ```

2. In FFXIV, open **LightlessSync settings > Diagnostics > Generate Diagnostics Report**. The analyzer looks for reports named `lightless_diagnostics_*.zip` directly in your LightlessSync configuration folder. Leave the report zipped.

3. Double-click `start.bat`, or run this from the project folder:

   ```powershell
   python app.py
   ```

4. Your browser should open at [http://localhost:8000](http://localhost:8000). Keep the terminal open while using the dashboard. Press **Ctrl+C** in the terminal to stop the server.

Choose your character, then select a group to inspect its players and overlaps. After generating a new report, click **Refresh Logs** to load it.

The network graph loads vis-network from unpkg, and the interface loads a font from Google Fonts. Those resources require an internet connection.

## Data sources

By default, the analyzer reads:

```text
%APPDATA%\XIVLauncher\pluginConfigs\LightlessSync
```

| File or folder | Purpose |
| --- | --- |
| `lightless_diagnostics_*.zip` | Group membership snapshots and player details; the latest report for the selected character is preferred. |
| `server.json` | Your character names and UIDs. |
| `notes.json` | Saved player and group notes used as display names. |
| `playerperformance.json` | Additional player names from auto-pause history. |
| `tracelog/*.log` | Active-character detection and fallback membership information. |

If your configuration is elsewhere, edit `DEFAULT_CONFIG_DIR` near the top of `app.py` to point to that folder.

Without a usable diagnostics report, the analyzer reconstructs memberships from join and leave events in trace logs. This can miss existing members, and the dashboard shows an **Incomplete Data** banner. Generate a fresh diagnostics report for more reliable results. Reports are snapshots, so regenerate them when memberships change. Trace-log fallback is not reliably separated by character.

The analyzer reads these files without modifying them. It does not upload your diagnostics or configuration to GitHub.

## Understanding the results

- **Shared players** appear in the selected group and at least one other analyzed group.
- **Unique players** appear only in the selected group within the analyzed data.
- **Redundancy** is the percentage of a group's players who also appear in other groups.
- **Leave impact** is based on the number of unique players:

  | Impact | Unique players |
  | --- | --- |
  | None | 0 |
  | Low | 1–3 |
  | Medium | 4–10 |
  | High | More than 10 |

A zero-impact group has no unique players in the current data. Assess groups one at a time: two groups can cover each other's players, so leaving every zero-impact group at once can still remove coverage. The app only reports results; it does not leave groups or change LightlessSync settings.

## GitHub Pages website

This repository includes a Jekyll project page. `index.md` reuses this README as the website content, and `_config.yml` sets its theme and project URL.

To publish it:

1. Commit and push the README, `index.md`, and `_config.yml` to `main`.
2. Open the repository's [Settings > Pages](https://github.com/ric6121824/LightlessGroupExaminer/settings/pages).
3. Set **Source** to **Deploy from a branch**.
4. Select **main** and **/(root)**, then click **Save**.
5. Wait for the Pages deployment in the [Actions tab](https://github.com/ric6121824/LightlessGroupExaminer/actions) to finish.

Once deployed, the project guide will be available at:

[https://ric6121824.github.io/LightlessGroupExaminer/](https://ric6121824.github.io/LightlessGroupExaminer/)

GitHub Pages serves static content and cannot run the Python backend or read your local LightlessSync folder. Opening `public/index.html` on Pages will therefore fail when it requests `/api/data`. Run `python app.py` locally to use the dashboard. See GitHub's documentation on [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and [publishing from a branch](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `python` is not recognized | Install Python 3 and enable its PATH option, or try `py app.py`. |
| Browser shows **Server Offline** | Keep `app.py` running and open `http://localhost:8000`; opening the HTML file directly does not start the API. |
| No groups or incomplete results | Check the configuration path, generate a diagnostics report for your character, and refresh. |
| Character is missing or has the wrong data | Check the character selector and ensure that character has a diagnostics ZIP in the configuration folder. |
| Port 8000 is already in use | Stop the process using it, or run `python -c "from app import run; run(port=8001)"` and open `http://localhost:8001`. |
| Network graph does not load | Check that your browser can load vis-network from unpkg. |
| GitHub website returns 404 | Confirm the Pages source is `main` / `/(root)`, the new files are pushed, and the Pages deployment succeeded. |

## Project layout

```text
app.py          Python analyzer and HTTP server, including /api/data
start.bat       Windows launcher
public/         Local dashboard HTML, CSS, and JavaScript
scratch/        Development and diagnostic scripts
README.md       Project documentation
index.md        GitHub Pages entry page
_config.yml     GitHub Pages / Jekyll configuration
```
