# Car‑Alert Pipeline

A lightweight, end‑to‑end toolkit that monitors online car auctions and alerts you when newly scraped vehicles match your personal search profile.

---

## Why use it?

* **Automated scrape → match loop** — the scraper walks result pages every day, parses cars **in *batches*** (default 10 links at a time), and immediately evaluates each batch against your saved queries so you don’t wait for the full crawl to finish.
* **Rolling YAML archive** — every parsed car is written to `data/vehicles_data_N.yaml` (≤3000 entries/file, UTF‑8) so nothing is lost between runs.
* **Tkinter GUI** — a small desktop app (`gui/gui_tool.py`) lets you add, edit, and delete query/ brand pairs on the fly.
* **One‑file YAML config** — all runtime knobs live in [`config/orchestrator.yaml`](config/orchestrator.yaml); no environment variables required.
* **Daily scheduler** — `scheduler.py` wraps APScheduler and can be pinned to any HH\:MM via CLI flags (`-H`, `-M`).
* **Clean logging** — three named loggers (*ArticleParser*, *Orchestrator*, *Scheduler*) stream to stdout.

---

## System Workflow

```
  [Scheduler] -(at HH:MM)-> [Orchestrator]
                          |
                          | daily cron
                          v
                +-------------------+
                | ArticleParser     |
                |  • scrape batch   |
                +-------------------+
                          |
                          | parsed vehicles
                          v
                +-------------------+     +---------------+
                |      Matcher      |<----| GUI (Tkinter) |
                |  • predict        |     +---------------+
                |  • log sent.yaml  |
                +-------------------+
                          |
                          | hits
                          v
                      [E‑mailer]
```
* **Scheduler** [scheduler.py](scheduler.py) launches the orchestrator on the configured timer.
* **Orchestrator** drives a streaming loop: it gives the **ArticleParser** the next batch of URLs, then hands the parsed cars to the **Matcher**.
* **Matcher** loads the latest [queries.json](data/queries.json), scores the cars, logs every matched URL to [sent.json](data/sent.json), and (optionally) triggers the e‑mailer.
* The **Tkinter GUI** run under [app.py](gui/app.py) sits outside the loop, allowing users to add / update queries; because the matcher reloads [queries.json](data/queries.json) each batch, changes propagate within minutes.

---

## GUI in depth

### Why a desktop GUI?

Editing `data/queries.json` by hand is error‑prone and inconvenient. The Tkinter front‑end is a quick, keyboard‑friendly way to add, tweak, or remove search rules without ever touching the filesystem for the user.
Because the matcher reloads the file every batch, changes made here take effect for the next batch run.

The Tkinter app **`gui/gui_tool.py`** is a two‑column manager for your search profile.

| Column        | Meaning                                                             | 
| ------------- |---------------------------------------------------------------------| 
| **Queries**   | Free‑form keyword string used by the matcher.                       |
| **Car brand** | Preferred manufacturer name, whitespace seperated (or leave blank). | 

### Controls

* **Add /↵Enter**— inserts a new row at the bottom, then clears both entry boxes.
* **Update**— overwrites the selected row; only the column(s) you edited change.
* **Delete(Del/⌫)**— removes the selected row(s); multi‑select with **Ctrl** or **Shift**.
* **Undo / Redo (Ctrl+Z /Y)**— full history while the window is open.
* **Finish**— writes changes to `data/queries.json` and exits.
* **Cancel**— exits without saving.
* **Help → Controls**— shows a popup with the same cheat‑sheet.

All edits are in‑memory until you click **Finish**; the matcher reloads `queries.json` at each batch so mid‑crawl edits take effect within \~10 cars.

---

## Quick start

### 1. Clone & install deps

```bash
git clone <repo>
cd car_alerts
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure once

Open [`config/orchestrator.yaml`](config/orchestrator.yaml) and set:

* **smtp.** — if you want e‑mail alerts (leave blank to disable)
* **scraper.** — `base_url`, `max_pages`, `batch_size`, etc.
* **matcher.threshold** — probability cut‑off for your own model

### 3. Manage queries (GUI)

```bash
python gui/app.py   # add rows → Finish to save queries.json
```

### 4. Run ad‑hoc scrape

Run with terminal from root directory 05_car_alerts

```bash
python orchestrator.py   # streams batches, logs progress
```

### 5. Schedule daily job

Run with terminal from root directory 05_car_alerts

```bash
python scheduler.py          # defaults 06:00 Europe/Berlin
python scheduler.py -H 15 -M 30
```

---

## System workflow

```
  [Scheduler] -(at HH:MM)-> [Orchestrator]
        |
        |  daily cron
        v
  +-------------------+
  | ArticleParser     |
  |  • scrape batch   |
  +-------------------+
         |
         | parsed vehicles
         v
  +-------------------+
  |    Matcher        |<-- queries.json
  |  • predict        |     ^
  |  • log to sent.yaml|    |
  +-------------------+     |
         | hits             |
         v                  |
     [E‑mailer]             |
                            |
  GUI (Tkinter) ------------+
```


---

## Current limitations / TO-DO 

* **Error handling** — Selenium failures are logged but not retried.
* **Duplicate GUI openings** — starting multiple GUI instances could race on `queries.json`.
* **Unknown Car Brand Names** — car brands are not all ascii encoded. But in the links they need to be. Since exact matches of the given car brands are used for prediction, using the wrong brand name might let matching urls slip through.
* **Time Overflow** — If the scraper for some reason takes longer than a day. The behaviour of the scheduler is unknown so far.
---

## Requirements

The [requirements.txt](requirements.txt) file has been generated using [pipdeptree](https://pypi.org/project/pipdeptree/). Therefore all dependecies are shown in a hiracical tree.

Here the Core installed libraries are shown, that are needed to run this module:

```text
selenium            # browser automation
beautifulsoup4      # HTML parsing
apscheduler         # job scheduling
pytz                # timezone handling
pyyaml              # YAML persistence
tk                  # Tkinter GUI (bundled with Python on most OS)
torch               # to load in the model
transformer         # to load in the model
```

---

## License

MIT 
