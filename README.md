# Personal Task Manager

A student task manager built with Streamlit and SQLite. Accounts and tasks stay
in a local database; no external service is used. Each account only sees its own
tasks.

## Features

- Add, edit, delete, complete, and reopen tasks.
- Choose a category, priority, due date, and task status.
- Filter tasks by status, priority, and category; sort by deadline, priority,
  status, category, or name.
- See pending, in-progress, completed, and overdue totals, a status chart,
  overdue tasks, and deadlines for the next seven days.
- Sign in with the seeded `admin` / `admin123` account or create another local
  account.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes.

The database, `tasks.db`, is created beside the application on first run. Back
up this file to keep your local accounts and tasks.

## Run on Windows

Use Python 3.10 or newer:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit. The server is configured to listen on
the loopback interface so the app is local to your computer.

## Run tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```
