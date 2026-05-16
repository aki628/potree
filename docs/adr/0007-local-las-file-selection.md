# ADR 0007: Select local LAS files with the browser File API

## Status

Accepted

## Context

`examples/sample_las_top_view.html` currently loads the default LAS file from the local development server:

- `../data/sample.las`
- `../data/sample_labels.xml`

ADR 0006 hardened the URL query path so `file=` and `labelMap=` must resolve under `/data/` and cannot point to external origins. The next requirement is to let the user select a `.las` file from the local PC while keeping the security posture:

- The selected local file must not be uploaded to the development server.
- The selected local file must not be fetched from a remote URL.
- The selected local file must not create a browser-visible object URL.
- The local development server must remain bound to `127.0.0.1`, not `0.0.0.0`.
- DOM output derived from file names must use `textContent` or HTML escaping.

## Decision

Add a local `.las` file picker to `examples/sample_las_top_view.html`.

The sample will not load a point cloud automatically on page load. It will prepare the validated local label map and wait for the user to select a local `.las` file. When the user selects a local file, the sample will:

1. Accept only files whose displayed name ends with `.las`.
2. Read the file through the browser File API with `file.stream().getReader()`.
3. Reuse the existing LAS parsing and rendering path after the bytes are read from the stream.
4. Display only the browser-provided file name and size; it will not display or infer a local filesystem path.
5. Escape file-name-derived strings before passing them to `viewer.setDescription(...)`.
6. Replace the existing rendered point group and base plane before adding the newly selected file, so repeated local loads do not stack geometry.
7. Continue loading the label map only through the already validated local `/data/*.xml` path.

This means local file selection is browser-local. The selected `.las` bytes stay in the page runtime unless the user has separately exposed the browser, machine, or development server.

## Consequences

- A user can inspect a local `.las` file without copying it into `data/`.
- The page no longer reads `../data/sample.las` automatically on startup.
- The browser will not send the selected file to `https://127.0.0.1:1234`.
- Query-based remote loading remains blocked by ADR 0006.
- The browser cannot expose the full local file path to JavaScript; only the file name is available.
- The sample remains a local viewer, not a remote upload service.

## Completion Criteria

1. This ADR exists and includes completion criteria.
2. `examples/sample_las_top_view.html` provides a local file input for `.las`.
3. The local file input does not use `URL.createObjectURL(...)`.
4. The local file input path does not call `fetch(...)` with the selected file.
5. Selected files are read through `File.stream().getReader()`.
6. Selected file names are displayed via `textContent` or passed through `escapeHTML(...)`.
7. A non-`.las` selected file is rejected before parsing.
8. Loading a second LAS file removes the previous point group and base plane from the scene.
9. The page does not automatically load `../data/sample.las` on startup.
10. External `file=` and `labelMap=` URL queries remain rejected by the existing validation.
11. `gulpfile.js` remains bound to `127.0.0.1` and does not bind to `0.0.0.0`.
12. The inline module script passes a syntax check.
13. The HTTPS development server returns `examples/sample_las_top_view.html`.
14. The HTTPS development server returns the default `data/sample_labels.xml`.

## Verification

Completed on 2026-05-16.

- `examples/sample_las_top_view.html` now has `<input id="las_file_input" type="file" accept=".las,.LAS">`.
- Static search confirmed `URL.createObjectURL(...)` is not used in `examples/sample_las_top_view.html`.
- The local file path uses `loadLasPointsFromFile(...)`, which validates the `.las` suffix before parsing.
- The local file path reads bytes with `file.stream().getReader()` and passes that reader to the shared LAS stream parser.
- The selected local file is not passed to `fetch(...)`; `fetch(...)` remains only in `loadLabelDefinitions(...)` for validated local XML and `loadLasPoints(...)` for the validated `/data/*.las` URL path.
- File names and source labels are written to status text through `textContent` or to Potree description through `escapeHTML(...)`.
- `clearLoadedSceneObjects(...)` removes and disposes the previous point group and base plane before adding the next LAS render.
- The page no longer calls `loadLasPoints(samplePath, ...)` on startup; it waits for local file selection.
- The existing `resolveLocalDataPath(...)` validation for `file=` and `labelMap=` remains in place and still rejects external origins and paths outside `/data/`.
- Static search confirmed `gulpfile.js` still has `host: '127.0.0.1'`; no `0.0.0.0` bind was added.
- `node` syntax validation of the inline module script completed with `inline module syntax ok`.
- A follow-up `npm start` attempt reported `EADDRINUSE` because `127.0.0.1:1234` was already in use.
- The already-listening HTTPS server on `https://127.0.0.1:1234` returned the updated sample page.
- `curl -k -sSf https://127.0.0.1:1234/examples/sample_las_top_view.html` returned the updated sample HTML, including the local LAS file input and `file.stream().getReader()` path.
- Static search confirmed the startup path sets `Select a local .las file to render.` instead of calling `loadLasPoints(samplePath, ...)`.
- `curl -k -sSf https://127.0.0.1:1234/data/sample_labels.xml` returned the default label XML.
