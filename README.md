# Canvas → Google Calendar MCP Server

Sync your Canvas assignments and exam dates (including a best-effort scan of syllabus PDFs) to Google Calendar via an MCP server.

---

## 0) Prerequisites

- Python **3.11+** (3.13 OK)
- A Canvas account with course access
- A Google account (Gmail easiest)
- (Optional) Outlook support is scaffolded but not required

---

## 1) Get the code & install dependencies

### Windows (PowerShell)
```powershell
cd C:\path\to\canvas-calendar-sync
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
