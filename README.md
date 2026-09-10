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
- The app displays an animated loader with real-time progress while securely exchanging tokens in the background, displays your account name and email, and remembers your session automatically!

---

## How to Use

1. **Sign In to Unlock Features**: On launch or when signed out, all interactive features are disabled and a prompt asks you to sign in. Click **🌐 Log In with Dropbox** in the banner or top header. Your connected account status (`● Connected: Name (email)`) will be displayed in the header and all features unlock immediately.
2. **Paste Link**: Enter or paste any Dropbox shared folder or file link into the **Dropbox Shared Link** box.
3. **Load Folders**: Click **🔍 Load Folders** (or press Enter). If the link is password-protected, the app automatically presents a popup dialog to enter the password, then loads the directory tree.
4. **Select Items**: Check or uncheck folders and files so you only download what you want.
5. **Start Download**: Click **▶ Start Download**. The app downloads **only the selected files** directly into your local destination folder, preserving the exact subfolder hierarchy.

---

## Features

- **Login-Gated Workspace**: All functional controls (link loading, destination configuration, directory tree selection, and downloading) remain locked until an account is connected, preventing unauthenticated API failures.
- **Dedicated Authentication Callout**: Prominent visual banner and locked tree placeholder asking the user to log in first, with 1-click OAuth activation.
- **Animated Login Loader**: Sleek modal loader dialog featuring an animated spinner badge, pulsing gradient progress bar, and real-time step status ("Exchanging authorization code...", "Connecting to Dropbox API...", "Retrieving account profile...") to keep the user informed.
- **Single Unified Link Input**: Clean, distraction-free link bar with smart automatic password prompting for password-protected links.
- **Modern User-Friendly UI**: Top-bar account status, compact download configuration, interactive selection tree, live metrics dashboard, and toggleable activity log.
- **User Account Login**: 1-click browser OAuth (PKCE) login with any Dropbox account. No secrets or manual token handling needed.
- **Session Persistence**: Remembers your login across launches; sign out or switch accounts anytime with one click.
- **Automatic Token Refresh**: Long-running downloads automatically refresh access tokens without session timeouts.
- **Direct Selective Download**: Downloads only the specific files you check in the tree. No 100+ GB full-archive downloads.
- **Automatic Password Unlock**: Automatically detects password-protected links and displays a modal prompt to unlock seamlessly.
- **Download Manager Controls (Pause & Resume)**: Instant pause and resume controls during active downloads with accurate paused duration compensation in elapsed time and transfer speed metrics.
- **Recent Links History**: Quick-access chip bar and dropdown history menu saving your recently scanned Dropbox links and folder names for 1-click reloading.
- **Smart Action State**: Dynamically enables and disables download buttons based on item selection, valid destination paths, and active connection status.
- **Interactive Directory Tree**: Expand/collapse folders, view item counts, formatted file sizes, file type icons, and right-click context menu for batch selecting or expanding subfolders.
- **Human-Friendly Error Guidance**: Clear, contextual error dialogs explaining link expirations, network interruptions, access permissions, and password requirements with actionable steps.
- **Smart Skip & Existing File Auto-Scan**: If an existing local file is detected, the system immediately scans the entire queue to identify and skip all other already downloaded files, instantly updating progress bars and transfer statistics before downloading the remaining files.
- **Direct Download Without Root Folder**: Files and folders download directly into your chosen destination folder without creating an unnecessary container folder named after the Dropbox shared link.
- **Smart Single Folder Destination Matching**: If you select 1 folder for download and your destination folder's name matches that folder (e.g. selecting an existing `Photos` folder for a Dropbox folder named `Photos`), files download directly into that folder without creating a duplicate nested folder (e.g. avoiding `Photos/Photos`). Top-level files in that folder are saved directly and only necessary subfolders are created.
- **Cryptographic File Integrity Verification**: Automatically verifies every downloaded and existing file using Dropbox's official SHA-256 block hash algorithm (`content_hash`) and exact byte counts to detect incomplete, missing, or corrupted files with 100% certainty.
- **Automatic Corruption Repair**: Automatically deletes corrupted or partially written local files and re-downloads fresh copies from Dropbox, re-verifying to ensure all files on disk are completely intact.
- **On-Demand File Verification**: A dedicated "🔍 Verify Files" button allows users to verify their local files against Dropbox cloud checksums at any time without having to re-download intact files.
- **Dual Progress Bars**: Individual file progress and overall batch progress with 100% completion confirmation.
- **Activity Log**: Searchable and filterable log console with one-click copy and clear.
- **Safe & Resilient**: Graceful cancellation, thread lifecycle management, temporary download files (`.tmp`), and path sanitization.
