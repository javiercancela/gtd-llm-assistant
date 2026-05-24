# macOS Shortcuts for GTD captures

These Shortcuts only write JSON drops into `GTD_WATCH_DIR`. The inbox processor
does all classification, reference storage, and source document copying.

## Finder Quick Action

Create a Shortcut named `Add to GTD references`.

1. Set it to receive `files` in `Finder`.
2. Add `Run Shell Script`.
3. Set input handling to `as arguments`.
4. Use this script, replacing `GTD_WATCH_DIR` if you do not source your normal
   env file in Shortcuts:

```bash
set -euo pipefail

WATCH_DIR="${GTD_WATCH_DIR:-$HOME/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents}"
mkdir -p "$WATCH_DIR"

for source_path in "$@"; do
  /usr/bin/python3 - "$WATCH_DIR" "$source_path" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

watch_dir = Path(sys.argv[1])
source_path = Path(sys.argv[2]).expanduser()
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
dest = watch_dir / f"file-reference-{stamp}.json"
dest.write_text(
    json.dumps({"source_path": str(source_path), "tags": []}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY
done
```

Python performs the JSON encoding, so selected paths are escaped as JSON instead
of interpolated into a string.

## Clipboard Capture

Create a Shortcut named `Capture clipboard to GTD`.

1. Add `Get Clipboard`.
2. Add `Run Shell Script`.
3. Set input handling to `to stdin`.
4. Use this script:

```bash
set -euo pipefail

WATCH_DIR="${GTD_WATCH_DIR:-$HOME/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents}"
mkdir -p "$WATCH_DIR"

/usr/bin/python3 - "$WATCH_DIR" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

watch_dir = Path(sys.argv[1])
text = sys.stdin.read()
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
dest = watch_dir / f"clipboard-{stamp}.json"
dest.write_text(
    json.dumps({"text": text, "tags": []}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY
```

Assign a keyboard shortcut in the Shortcut details if you want a hotkey.

## Notes

- `.txt`, `.md`, and `.markdown` are read directly.
- `.docx`, `.odt`, `.rtf`, `.html`, `.htm`, and `.epub` require pandoc:
  `brew install pandoc`.
- PDF extraction is intentionally unsupported in v1.
- Shortcuts never copy documents into `references/`; `uv run main` does that
  only after a reference row is created.
