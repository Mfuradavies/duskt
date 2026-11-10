# duskt

A simple keyboard-first terminal video and audio downloader.

## Download

1. Open the repository's **Releases** page:
   <https://github.com/Mfuradavies/duskt/releases>
2. Open the newest release.
3. Download the file for your operating system:

   | Operating system | Download |
   |---|---|
   | Linux, 64-bit | `duskt-linux-x86_64` |
   | Windows, 64-bit | `duskt-windows-x86_64.exe` |
   | macOS, Intel | `duskt-macos-x86_64` |

Do not download the source code archive. Download only the executable for your
computer.

## Run

### Linux

Open a terminal in the folder containing the download:

```bash
chmod +x duskt-linux-x86_64
./duskt-linux-x86_64
```

### macOS

Open Terminal in the folder containing the download:

```bash
chmod +x duskt-macos-x86_64
./duskt-macos-x86_64
```

If macOS blocks the app, open **System Settings → Privacy & Security** and
approve the blocked executable, then run the command again.

This release targets Intel Macs. Apple Silicon Macs may need Rosetta 2.

### Windows

Open PowerShell in the folder containing the download:

```powershell
.\duskt-windows-x86_64.exe
```

If Windows SmartScreen appears, verify that you downloaded the executable from
the official GitHub Releases page before choosing **More info → Run anyway**.

#### Run `duskt` from any CMD directory

The Windows download is a portable executable; you do not need to reinstall or
open it from the Downloads folder each time. To make `duskt` available from
anywhere:

1. Create a permanent folder, for example
   `%LOCALAPPDATA%\Programs\Duskt`, and move
   `duskt-windows-x86_64.exe` into it.
2. Rename the file to `duskt.exe`.
3. In the Start menu, search for **Edit environment variables for your
   account** and open it.
4. Under **User variables**, select **Path** → **Edit** → **New**, then add
   `%LOCALAPPDATA%\Programs\Duskt`. Confirm each dialog with **OK**.
5. Close and reopen Command Prompt. You can now run `duskt` from any folder.

## Use duskt

1. Paste a video or playlist URL and press **Enter**.
2. For a playlist, use **Up/Down** to move, **Space** to select videos, and
   **Enter** to continue.
3. Use **Space** to select one or more video or audio formats.
4. Press **Enter** to start downloading.
5. Press **Q** to quit.

On Windows, if normal `Ctrl+V` does not paste in the terminal, try
`Ctrl+Shift+V` or `Shift+Insert`. Duskt also reads the system clipboard through
these fallback shortcuts.

Playlists are limited to the first 25 items. YouTube titles remain unchanged.
Downloads are saved to:

```text
~/Downloads
```

On Windows, this means the user's standard Downloads folder.

## Notes

- Use an interactive terminal; duskt is a terminal application, not a windowed
  desktop app.
- The terminal should support Unicode characters for the best display.
- If FFmpeg is unavailable, Duskt hides formats that require merging separate
  video and audio streams. Audio-only and single-file video formats remain
  available.
- Only download content you are authorized to save and use.
