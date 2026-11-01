# duskt

A minimal, keyboard-friendly terminal video downloader using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [Textual](https://textual.textualize.io/).

## Run from source

```bash
python -m venv .venv
. .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e .
duskt
```

Paste a URL and press Enter. Confirm the fixed YouTube title, then use the format picker:
arrow keys move, Space selects multiple formats, and Enter starts the downloads.
Files are saved to `~/downloads` in the user's home directory.
The format list includes both video qualities and audio-only formats.

Playlist URLs show up to 25 songs in a video selector before the format selector.
YouTube titles are kept unchanged and cannot be edited.

## Build a standalone executable

Install the build extra and run PyInstaller:

```bash
python -m pip install -e ".[build]"
python -m PyInstaller --clean --noconfirm --onefile --name duskt \
  --paths src --add-data "src/duskt/app.tcss:duskt" src/duskt/__main__.py
```

The executable is written to `dist/`. Test it from the project directory:

```bash
./dist/duskt                 # Linux/macOS
dist\\duskt.exe              # Windows
```

### Shipping to other users

PyInstaller bundles Python and Duskt's dependencies, so recipients do not need
Python, Textual, yt-dlp, or a compiler installed. Builds are platform-specific:
build each artifact on the operating system it targets (or use a matching CI
runner). Do not copy a Linux binary to Windows or macOS.

#### Linux

Build on Linux and distribute `dist/duskt`. Mark it executable if needed:

```bash
chmod +x dist/duskt
./dist/duskt
```

#### macOS

Build on macOS and distribute `dist/duskt`. If macOS blocks an unsigned binary,
the user can approve it in **System Settings → Privacy & Security**, or you can
sign/notarize it before shipping.

#### Windows

Build on Windows and distribute `dist\\duskt.exe`. The user can open it from
PowerShell:

```powershell
.\dist\duskt.exe
```

Downloads are saved in `downloads` under the user's home directory, regardless
of where Duskt is started. Users need write permission there. The terminal must
support interactive keyboard input and Unicode characters for the best display.

For release archives, include only the platform executable and a short copy of
these run instructions. Keep `build/`, `dist/`, and generated spec files out of
source control.

### Publish one-file GitHub releases

The repository includes a GitHub Actions workflow at
`.github/workflows/release.yml`. It builds separate one-file executables for
Linux x86-64, Windows x86-64, and macOS Intel, then attaches them to a GitHub
Release.

To publish a release:

1. Commit and push your changes.
2. Create and push a version tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. Open the **Actions** tab and wait for the workflow to finish.
4. Open the generated GitHub Release and download the asset for the user's OS.

Each user downloads exactly one executable:

```text
duskt-linux-x86_64
duskt-windows-x86_64.exe
duskt-macos-x86_64
```

On Linux and macOS, the user may need to run `chmod +x` after downloading.
macOS may also require approval in **System Settings → Privacy & Security**
because the binary is unsigned.

Video formats that combine separate video and audio streams require FFmpeg.
For a truly dependency-free release, either ship a platform FFmpeg binary and
add it to the application, or select a format labeled as a single-file stream.

The interface follows the palette, spacing, borders, progress treatment, and icon guidance in [DESIGN.md](DESIGN.md).
