# ADR 0005: Serve `sample_las_top_view.html` over local HTTPS

## Status

Accepted

## Context

`examples/sample_las_top_view.html` is run through `npm start`, which executes `gulp watch` and starts the `gulp-connect` development server on port `1234`.

The current server is bound to `127.0.0.1`, which is desirable because it keeps the development server local. However, it uses plain HTTP:

```js
connect.server({
  host: '127.0.0.1',
  port: 1234,
  https: false,
});
```

The sample should be operable over HTTPS while preserving the local-only binding. This is useful when testing browser behavior that expects a secure context and avoids changing the previous security guidance about not exposing port `1234` externally.

`gulp-connect` supports HTTPS by setting `https: true`. In that mode it uses its bundled self-signed development certificate.

## Decision

Change the local development server for `npm start` from HTTP to HTTPS by setting `https: true` in `gulpfile.js`.

Keep:

- `host: '127.0.0.1'`
- `port: 1234`

Do not add `host: '0.0.0.0'`.

## Consequences

- The sample should be opened at:

```text
https://127.0.0.1:1234/examples/sample_las_top_view.html
```

- The browser will likely show a warning because the development certificate is self-signed.
- `http://127.0.0.1:1234/...` will no longer be the intended URL for `npm start`.
- Relative asset paths in `sample_las_top_view.html` should continue to work because they are protocol-relative to the same local origin.
- The server remains local-only and should not be reachable from other machines unless an external port-forwarding or proxy layer is added outside this repo.

## Completion Criteria

1. `gulpfile.js` configures `gulp-connect` with `https: true`.
2. `gulpfile.js` keeps `host: '127.0.0.1'` and does not bind to `0.0.0.0`.
3. `npm start` starts a server that logs an HTTPS URL on port `1234`.
4. `curl -k https://127.0.0.1:1234/examples/sample_las_top_view.html` returns the sample HTML.
5. `curl http://127.0.0.1:1234/examples/sample_las_top_view.html` does not return the normal sample HTML over plain HTTP.
6. The returned HTTPS HTML still references the local sample scripts and module import paths used by `sample_las_top_view.html`.

## Verification

Completed on 2026-05-16.

- `gulpfile.js` now has `host: '127.0.0.1'`, `port: 1234`, and `https: true`.
- `gulpfile.js` does not bind the development server to `0.0.0.0`.
- `npm start` logged `Server started https://127.0.0.1:1234`.
- `curl -k -sSf https://127.0.0.1:1234/examples/sample_las_top_view.html` returned the sample HTML.
- `curl -sS -i http://127.0.0.1:1234/examples/sample_las_top_view.html` returned `Empty reply from server`, so the normal sample HTML was not served over plain HTTP.
- The HTTPS HTML still contains local references including:
  - `../libs/jquery/jquery-3.1.1.min.js`
  - `../build/potree/potree.js`
  - `../libs/three.js/build/three.module.js`
  - `../data/sample.las`
  - `../data/sample_labels.xml`
- `curl -k -sSf https://127.0.0.1:1234/data/sample_labels.xml` returned the default label XML.
- `curl -k -sSf -I https://127.0.0.1:1234/data/sample.las` returned `HTTP/2 200`.
