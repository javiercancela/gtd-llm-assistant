# Plan: Local document references from Mac files and clipboard

## 0. Decision summary

I agree with the proposed direction: implement **Option 1 + Option 3**.

- **Option 1:** extend capture JSON so producers can point to a local source file.
- **Option 3:** add thin macOS Shortcut / Quick Action producers that write capture JSON into the existing watch folder.

This preserves the current architecture: producers only drop JSON, `main` owns processing, Gemini still classifies captures, and references still persist through the existing SQLite reference store.

One implementation adjustment: store copied source documents under `GTD_INBOX_DIR/references`, not under the Shortcuts `GTD_WATCH_DIR`. In this repo, `watch_dir` is the external producer drop zone, while `processed/` and `logs/` already live under `inbox_dir`. The owned reference files should live beside those processor-owned folders.

## 1. Scope

In scope for v1:

- Capture JSON with `source_path`.
- `.md`, `.markdown`, and `.txt` direct text extraction.
- Pandoc-backed extraction for `.docx`, `.odt`, `.rtf`, `.html`, and `.epub`.
- Full extracted text stored in `metadata.full_text`.
- Source file copied into `references/` after a reference row is created.
- Copied file path stored in `metadata.file_path`.
- Source file SHA-256 stored in `metadata.content_hash`.
- Duplicate source files deduped by `metadata.content_hash`.
- Clipboard Shortcut that writes current clipboard text as ordinary `{ "text": ... }` capture JSON.
- Finder Quick Action / Shortcut that writes `{ "source_path": ... }` capture JSON.
- Documentation for installing the Shortcuts manually.

Out of scope for v1:

- PDF extraction.
- Chunking one document into multiple references.
- MCP file-ingestion tools.
- Editing or deleting copied source documents.
- Automatically watching folders such as `~/Downloads`.
- Any in-repo automation that installs macOS Shortcuts for the user.

## 2. Capture contract

Existing text captures keep working:

```json
{
  "text": "Save this as a reference",
  "url": "https://example.com",
  "tags": ["example"]
}
```

New file captures add `source_path`:

```json
{
  "source_path": "/Users/javier.cancela/Downloads/contract.docx",
  "tags": []
}
```

Rules:

- `source_path` must be an absolute local path after `~` expansion.
- If both `text` and `source_path` are present, fail the capture with a clear log message in v1. Supporting both is unnecessary until there is a real use case.
- The processor reads and extracts `source_path` before classification, then adds extracted markdown/text into `capture["text"]`.
- The original source file is never modified.
- The capture JSON remains in place on failure so the existing retry behavior still applies.

## 3. Workflow

Example: downloaded document at `/Users/javier.cancela/Downloads/contract.docx`.

1. User right-clicks the file in Finder and runs "Add to GTD references".
2. The Shortcut writes a JSON file into `GTD_WATCH_DIR`, for example:

   ```json
   {
     "source_path": "/Users/javier.cancela/Downloads/contract.docx",
     "tags": []
   }
   ```

3. `uv run main` picks up the JSON file.
4. The processor expands and validates `source_path`.
5. The document extractor converts the document to markdown text.
6. The processor sets `capture["text"]` to the extracted text and stores file metadata in an internal context object.
7. Gemini classifies the capture normally.
8. If the classified item is an English reference, `save_reference` persists the row.
9. After the row is created, the processor copies the original file to:

   ```text
   ${GTD_INBOX_DIR}/references/YYYY-MM-DD_<content-hash-prefix>_contract.docx
   ```

10. The saved reference metadata includes:

    ```json
    {
      "source_capture": "drop.json",
      "source_path": "/Users/javier.cancela/Downloads/contract.docx",
      "file_path": "/Users/javier.cancela/Library/Mobile Documents/com~apple~CloudDocs/GTD/00_Inbox/references/2026-05-24_ab12cd34_contract.docx",
      "content_hash": "ab12cd34..."
    }
    ```

11. The original capture JSON moves to `processed/`.
12. The original file in `~/Downloads` can be deleted without losing the canonical reference file.

Clipboard captures are simpler:

1. User runs a keyboard Shortcut.
2. The Shortcut writes `{ "text": "<clipboard text>", "tags": [] }`.
3. The existing text capture path handles it.
4. No source file is copied and no `metadata.file_path` is added.

## 4. Code design

Keep the change small and aligned with the current layers.

### 4.1 Configuration

Change `src/gtd_assistant/infrastructure/config.py`:

- Add `references_dir: Path` to `InboxConfig`.
- Add optional env var `GTD_REFERENCES_DIR`.
- Default to `inbox_dir / "references"`.

Update:

- `config/env.example`
- `README.md`
- `ARCHITECTURE.md`

### 4.2 File extraction port

Add a port:

```python
class DocumentTextExtractor(Protocol):
    def extract_text(self, path: Path) -> str:
        """Return markdown/plain text extracted from a supported local document."""
```

Place it at:

```text
src/gtd_assistant/ports/document_text_extractor.py
```

Add an adapter:

```text
src/gtd_assistant/adapters/local_documents/extractor.py
```

Adapter behavior:

- `.txt`, `.md`, `.markdown`: read UTF-8 text directly.
- `.docx`, `.odt`, `.rtf`, `.html`, `.htm`, `.epub`: run `pandoc --from <format> --to gfm --wrap=none <path>`.
- Unsupported extensions raise a clear `ValueError`.
- Missing `pandoc` raises a clear runtime error telling the user to install it, for example `brew install pandoc`.
- Empty extracted text raises a clear `ValueError`.

Do not add PDF support in this adapter yet.

### 4.3 Capture preparation use case

Add a small application module:

```text
src/gtd_assistant/application/prepare_capture.py
```

Responsibilities:

- Accept a raw capture dict and the capture file name.
- If there is no `source_path`, return the capture unchanged and no file context.
- If `source_path` exists:
  - validate the capture does not also provide `text`;
  - expand and resolve the source path;
  - verify it is a file;
  - compute SHA-256 from source file bytes;
  - extract text through `DocumentTextExtractor`;
  - return a new capture dict with `text` populated;
  - return a `SourceDocument` context containing original path, original file name, extension, content hash, and extracted text.

Keep `adapters/icloud/json_reader.py` unchanged except for tests if needed. Its job is only JSON reading and iCloud hydration.

### 4.4 File dedupe

The current `ReferenceStore` can find by URL and dedupe key, but not metadata. Add the narrow method needed by this feature:

```python
def find_by_content_hash(self, content_hash: str) -> ReferenceRecord | None:
    """Return an existing reference whose metadata.content_hash matches."""
```

SQLite implementation:

- Query `json_extract(metadata_json, '$.content_hash') = ?`.
- Add an expression index if useful:

  ```sql
  CREATE INDEX IF NOT EXISTS idx_references_content_hash
    ON reference_records(json_extract(metadata_json, '$.content_hash'));
  ```

Fallback note: SQLite JSON1 is expected on modern macOS/Python. If tests show it is unavailable, use a simple scan fallback because this is a personal-size database.

### 4.5 Save reference metadata

Change `application/save_reference.py` conservatively:

- Add optional parameter `source_document: SourceDocument | None = None`.
- If `source_document` exists:
  - check `store.find_by_content_hash(source_document.content_hash)` before embedding;
  - add `metadata.full_text`;
  - add `metadata.source_path`;
  - add `metadata.content_hash`;
  - leave `url` unchanged; do not store `file://` URLs in `url`.

Important: `metadata.file_path` is not known until after the row is created and the file copy destination is chosen. Add the copied-file metadata with a repository update method, not by overloading create-time data.

Add to `ReferenceStore`:

```python
def update_metadata(self, reference_id: int, metadata: dict[str, Any]) -> ReferenceRecord:
    """Replace reference metadata and return the updated record."""
```

### 4.6 Owned file copy

Add a tiny application helper:

```text
src/gtd_assistant/application/archive_source_document.py
```

Responsibilities:

- Create `references_dir`.
- Build a stable destination name:

  ```text
  YYYY-MM-DD_<hash-prefix>_<sanitized-original-name>
  ```

- If the same destination already exists and has the same hash, reuse it.
- If a name collision exists with different bytes, append a short numeric suffix.
- Copy with `shutil.copy2`.
- Return the copied file path.

Call this only after `save_reference` returns `status == "created"`. If a file capture dedupes by content hash, do not copy another file.

### 4.7 Inbox processor wiring

Change `src/gtd_assistant/application/process_inbox_run.py`:

- Extend `InboxRunConfig` protocol with `references_dir: Path`.
- Extend `InboxRunDependencies` with `document_text_extractor: DocumentTextExtractor | None = None`.
- After reading capture JSON, call `prepare_capture`.
- Pass the prepared capture to `classify_capture`.
- Pass `source_document` to `save_reference`.
- If a reference was created and `source_document` exists:
  - copy the file into `references_dir`;
  - update reference metadata with `file_path`.
- Log:
  - extraction start/success with source filename and byte hash prefix;
  - copied source destination;
  - unsupported file or pandoc failures as errors.

Leave task/project/waiting-for publishing unchanged.

### 4.8 Delivery wiring

Change `src/gtd_assistant/delivery/cli.py`:

- Instantiate `PandocDocumentTextExtractor`.
- Pass it into `InboxRunDependencies`.

Do not wire anything into the MCP server for v1.

### 4.9 Shortcuts documentation

Add documentation under:

```text
docs/macos-shortcuts.md
```

Include:

- Finder Quick Action steps:
  - accepts files in Finder;
  - shell script receives selected file path;
  - writes a timestamped JSON file to `GTD_WATCH_DIR`;
  - uses JSON escaping, not string interpolation.
- Clipboard Shortcut steps:
  - gets clipboard text;
  - writes ordinary text capture JSON to `GTD_WATCH_DIR`.
- A note that Shortcuts only produce JSON and never copy documents into `references/`.

Add small helper scripts only if they keep the Shortcut setup simpler and testable. Prefer scripts that print JSON to stdout over scripts that know pipeline internals.

## 5. Implementation steps

### Step 1: Add config for owned reference files

Files:

- `src/gtd_assistant/infrastructure/config.py`
- `config/env.example`
- `README.md`
- `ARCHITECTURE.md`

Work:

- Add `references_dir`.
- Default it to `inbox_dir / "references"`.
- Document `GTD_REFERENCES_DIR`.

Verify:

- Unit test config default and env override.
- `uv run pytest tests/test_process_inbox_run.py tests/test_references.py`

### Step 2: Add document extraction port and adapter

Files:

- `src/gtd_assistant/ports/document_text_extractor.py`
- `src/gtd_assistant/adapters/local_documents/extractor.py`
- `tests/test_local_document_extractor.py`

Work:

- Implement direct text reads for markdown/plain text.
- Implement pandoc subprocess extraction for supported rich formats.
- Keep PDF explicitly unsupported.

Verify:

- Direct-read tests for `.md` and `.txt`.
- Unit test that `.pdf` raises unsupported-extension error.
- Unit test with fake subprocess runner for `.docx`, avoiding a real pandoc dependency in the test.
- Optional local smoke check: `pandoc --version`.

### Step 3: Prepare file-backed captures before classification

Files:

- `src/gtd_assistant/application/prepare_capture.py`
- `tests/test_prepare_capture.py`

Work:

- Introduce `SourceDocument`.
- Validate `source_path`.
- Compute SHA-256.
- Extract text.
- Return prepared capture plus source context.

Verify:

- Text-only capture returns unchanged.
- File capture populates `text`.
- Capture with both `text` and `source_path` fails clearly.
- Missing source file fails clearly.

### Step 4: Add content-hash dedupe and metadata update support

Files:

- `src/gtd_assistant/ports/reference_store.py`
- `src/gtd_assistant/adapters/sqlite_reference_store/schema.py`
- `src/gtd_assistant/adapters/sqlite_reference_store/repository.py`
- `tests/fakes/reference_store.py`
- `tests/test_references.py`

Work:

- Add `find_by_content_hash`.
- Add `update_metadata`.
- Add SQLite content-hash lookup.
- Add a metadata update method that preserves all other record fields.

Verify:

- SQLite can find a row by `metadata.content_hash`.
- Updating metadata persists and returns the updated record.
- Existing URL and content dedupe tests still pass.

### Step 5: Extend `save_reference` for source documents

Files:

- `src/gtd_assistant/application/save_reference.py`
- `tests/test_references.py`

Work:

- Accept `source_document`.
- Dedupe by content hash before embedding.
- Store `full_text`, `source_path`, and `content_hash` in metadata.
- Do not store local file paths in `url`.

Verify:

- Re-adding the same source file hash returns `deduped`.
- Deduped file reference does not call the embedder.
- Created file reference metadata includes `full_text`, `source_path`, and `content_hash`.

### Step 6: Copy owned source files after successful creation

Files:

- `src/gtd_assistant/application/archive_source_document.py`
- `tests/test_archive_source_document.py`

Work:

- Copy source files into `references_dir`.
- Generate stable sanitized destination names.
- Reuse existing identical copied files.
- Avoid overwriting different files.

Verify:

- Copy creates expected file.
- Existing same-hash destination is reused.
- Name collision with different bytes produces a distinct file.

### Step 7: Wire file-backed captures into the inbox run

Files:

- `src/gtd_assistant/application/process_inbox_run.py`
- `src/gtd_assistant/delivery/cli.py`
- `tests/test_process_inbox_run.py`

Work:

- Add the extractor dependency.
- Prepare captures before classification.
- Pass source document context into `save_reference`.
- On created file references, copy source file and update metadata with `file_path`.

Verify:

- File capture classified as reference creates one SQLite/fake reference row.
- The original source file remains untouched.
- The copied file exists under `references_dir`.
- Metadata includes `file_path`.
- Failed extraction leaves the capture JSON in the watch folder.
- Non-reference task captures still publish as before.

### Step 8: Add macOS Shortcut documentation and optional helper scripts

Files:

- `docs/macos-shortcuts.md`
- Optional `scripts/write-file-reference-capture.py`
- Optional `scripts/write-clipboard-capture.py`

Work:

- Document Finder Quick Action setup.
- Document clipboard hotkey setup.
- If helper scripts are added, keep them producer-only: they write JSON to `GTD_WATCH_DIR` and do not import application/adapters.

Verify:

- Run helper script against a temp watch dir and inspect JSON.
- Run one manual Shortcut-created capture end to end with `uv run main`.

### Step 9: End-to-end verification

Run:

```bash
uv run pytest
uv run main
```

Manual checks:

- Add a `.md` from `~/Downloads`; confirm a reference row is created and file is copied.
- Add the same file again; confirm it dedupes and does not create another copied artifact.
- Add a `.docx`; confirm pandoc extraction produces useful markdown and metadata contains full text.
- Paste text from clipboard through the Shortcut; confirm it behaves like a normal text capture.
- Search/list references through the existing MCP tools and confirm metadata is visible on `get_reference`.

## 6. Risks and decisions to watch

- **Long documents:** storing full extracted text in metadata can grow the SQLite file quickly. This is accepted for v1 because the user explicitly chose one reference plus full text in metadata.
- **Gemini prompt size:** classification should use extracted text as-is initially. If real documents hit model limits or become expensive, add a small truncation step for classification while still storing full text in metadata.
- **Pandoc availability:** pandoc is a system dependency, not a Python dependency. The error path must be clear.
- **Sensitive files:** copied source files become part of the canonical GTD store. The Shortcut should be explicit enough that users understand they are archiving the selected file.
- **`url` semantics:** keep `url` for web URLs only. Local file paths belong in metadata.

## 7. Success criteria

The feature is complete when:

- A capture JSON with `source_path` can classify and save a document as an English reference.
- The reference row contains `metadata.full_text`, `metadata.source_path`, `metadata.content_hash`, and `metadata.file_path`.
- The original file is copied into `GTD_INBOX_DIR/references`.
- Re-adding the same file dedupes by SHA-256 and does not create a second reference.
- Clipboard text captures work through the existing text path.
- Unsupported formats, missing files, and missing pandoc fail with clear logs and leave the capture JSON retryable.
- `uv run pytest` passes.
