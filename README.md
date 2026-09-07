# Dropbox Recursive Downloader Pro — GUI

A simple and fast desktop application built with PySide6 for selectively downloading files and directory structures directly from Dropbox shared links without ever having to download huge root archive bundles.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

---

## 🔑 Dropbox User Login Setup

The application uses standard Dropbox PKCE OAuth for secure user sign-in directly in your browser. No app secret or manual access tokens are required!

### 1. Configure `DROPBOX_APP_KEY` in `.env`
Copy `.env.example` to `.env` (or edit `.env`):
```bash
# In .env:
DROPBOX_APP_KEY=your_dropbox_app_key_here
```

To get your App Key:
1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps).
2. Click **Create app** → choose **Scoped access** → select **Full Dropbox** → name your app.
3. Under the **Permissions** tab, check:
   - `files.metadata.read`
   - `sharing.read`
   Click **Submit**.
4. Under the **Settings** tab, copy the **App key** (Client ID) into your `.env` file as `DROPBOX_APP_KEY=...`.

### 2. Sign In with Your Dropbox Account
When you open the app:
- Click **🌐 Log In with Dropbox**.
- Your browser opens the Dropbox authorization page.
- **Sign into ANY Dropbox account you want** (personal, work, or client account) and click **Allow**.
- Copy the authorization code shown on screen and paste it into the prompt.
- The app connects to your account, displays your account name and email, and remembers your session automatically!

---

## How to Use

1. **Sign In**: Click **🌐 Log In with Dropbox** in Section 1. Your connected account status (`● Connected: Name (email)`) will be displayed.
2. **Paste Link**: Enter or paste any Dropbox shared folder link into the **Dropbox Shared Link** box. (If the link is password-protected, enter the password in the password field).
3. **Load Folders**: Click **🔍 Load Folders** (or let auto-scan run). The app inspects the shared folder and displays the directory tree.
4. **Select Items**: Check or uncheck folders and files so you only download what you want.
5. **Start Download**: Click **▶ Start Download**. The app downloads **only the selected files** directly into your local destination folder, preserving the exact subfolder hierarchy.

---

## Features

- **User Account Login**: 1-click browser OAuth (PKCE) login with any Dropbox account. No secrets or manual token handling needed.
- **Session Persistence**: Remembers your login across launches; sign out or switch accounts anytime with one click.
- **Automatic Token Refresh**: Long-running downloads automatically refresh access tokens without session timeouts.
- **Direct Selective Download**: Downloads only the specific files you check in the tree. No 100+ GB full-archive downloads.
- **Password-Protected Links**: Supports password-protected Dropbox links with password entry.
- **Interactive Directory Tree**: Expand/collapse folders, view item counts, formatted file sizes, and file type icons.
- **Live Metrics Dashboard**: Real-time download speed (MB/s), bytes transferred, files completed, and elapsed time.
- **Dual Progress Bars**: Individual file progress and overall batch progress.
- **Smart Skip**: Skips files that already exist locally with matching file size.
- **Activity Log**: Searchable and filterable log console with one-click copy and clear.
- **Safe & Resilient**: Graceful cancelation, temporary download files, and path sanitization.
