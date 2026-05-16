# ADR 0006: Harden `sample_las_top_view.html` query inputs

## Status

Accepted

## Context

The security notes under `docs/explanation/` identify several risks around `examples/sample_las_top_view.html`:

- `file=` and `labelMap=` can point the browser at external URLs.
- URL-derived strings are included in `viewer.setDescription(...)`, and Potree renders that description with jQuery `.html(...)`.
- Label names are already rendered with `textContent`, which should remain unchanged.
- Label colors are already restricted to `#rgb` and `#rrggbb`, which should remain unchanged.
- Large numeric query values can make the browser allocate excessive memory, especially `chunkPoints`, because it controls typed-array chunk capacity.
- The local development server should remain bound to `127.0.0.1` and should not be changed to `0.0.0.0`.

## Decision

Harden only `examples/sample_las_top_view.html` for this change.

The sample will:

1. Resolve `file=` and `labelMap=` through a local URL validation helper.
2. Reject external origins for `file=` and `labelMap=`.
3. Restrict the resolved path to `/data/`.
4. Restrict `file=` to `.las`.
5. Restrict `labelMap=` to `.xml`.
6. Escape all URL-derived strings before passing them to `viewer.setDescription(...)`.
7. Keep label names rendered with `textContent`.
8. Keep label colors validated by `normalizeHexColor(...)`.
9. Clamp numeric query values to bounded ranges before use.

The sample will continue to support the existing defaults:

- `../data/sample.las`
- `../data/sample_labels.xml`

## Consequences

- URLs such as `?file=https://example.com/sample.las` will no longer be accepted.
- URLs such as `?labelMap=https://example.com/labels.xml` will no longer be accepted.
- A local path outside `/data/` will no longer be accepted by this sample.
- This narrows the sample from a flexible arbitrary-URL loader to a local demo viewer. That is intentional for this security-focused example.
- Users who need external datasets should create a separate example with explicit CORS, trust, and authentication decisions.

## Completion Criteria

1. `examples/sample_las_top_view.html` validates `file=` and `labelMap=` before `fetch(...)`.
2. `file=` and `labelMap=` reject external origins.
3. `file=` and `labelMap=` reject paths outside `/data/`.
4. `file=` accepts only `.las`; `labelMap=` accepts only `.xml`.
5. `viewer.setDescription(...)` no longer receives raw URL-derived strings.
6. Label names still use `textContent`, not `.html(...)`.
7. Label colors still pass through `normalizeHexColor(...)`.
8. `chunkPoints`, `maxPoints`, `maxReadPoints`, and `pointSize` are clamped to explicit bounds.
9. The default HTTPS sample page still returns successfully from `https://127.0.0.1:1234/examples/sample_las_top_view.html`.
10. Default `sample.las` and `sample_labels.xml` still return successfully over HTTPS.
11. A malicious URL query containing HTML is escaped in the returned HTML source or rejected by the runtime validation path; it is not intentionally inserted as HTML.
12. `gulpfile.js` remains bound to `127.0.0.1` and does not bind to `0.0.0.0`.

## Verification

Completed on 2026-05-16.

- `examples/sample_las_top_view.html` now resolves `file=` and `labelMap=` through `resolveLocalDataPath(...)` before they are passed to `fetch(...)`.
- `resolveLocalDataPath(...)` rejects values whose `URL.origin` differs from `window.location.origin`.
- `resolveLocalDataPath(...)` requires resolved paths to start with `/data/`.
- `resolveLocalDataPath(...)` requires `.las` for `file=` and `.xml` for `labelMap=`.
- `viewer.setDescription(...)` now receives `escapeHTML(samplePath)` and `escapeHTML(labelMapPath)`, not the raw query-derived strings.
- Static search confirmed label display still uses `textContent`.
- Static search confirmed label colors still pass through `normalizeHexColor(...)`.
- `maxPoints`, `maxReadPoints`, `pointSize`, and `chunkPoints` now pass through `parseBoundedQueryNumber(...)`.
- `node` syntax validation of the inline module script completed with `inline module syntax ok`.
- `npm start` logged `Server started https://127.0.0.1:1234`.
- `curl -k -sSf https://127.0.0.1:1234/examples/sample_las_top_view.html` returned the sample HTML and showed the hardened helper code.
- `curl -k -sSf -I https://127.0.0.1:1234/data/sample.las` returned `HTTP/2 200`.
- `curl -k -sSf https://127.0.0.1:1234/data/sample_labels.xml` returned the default label XML.
- `rg` confirmed `gulpfile.js` still has `host: '127.0.0.1'` and `https: true`; no `0.0.0.0` bind was added.
