# ソースコード変更箇所と `.gitignore` 確認

作成日: 2026-05-17

## 結論

現在のワークツリーでは、ソースコードの未コミット差分はありません。

```text
git status --short --untracked-files=all
?? docs/explanation/sample_las_top_view_current_security_review.md
?? docs/explanation/source_changes_and_gitignore_review.md
?? docs/explanation/verify_npm_start_loopback_bind.md
```

現在未追跡なのは上記3つのMarkdownだけです。`examples/sample_las_top_view.html` と `gulpfile.js` のソースコード変更は、すでに直近コミットに入っています。

`.gitignore` については、`src/`、`examples/sample_las_top_view.html`、`gulpfile.js` のようなソースコード本体を無視する設定は見つかりませんでした。

一方で、`data/` は `.gitignore` で無視されています。そのため、新しく `data/` 配下に置いた `.las` や `.xml` は、明示的に `git add -f` しない限りGit管理対象になりません。

## 直近でソースコードに入った変更

確認対象の基準は、作業前に近い `55164ffb Merge branch 'develop'` から現在の `HEAD` までです。

```text
git diff --stat 55164ffb..HEAD -- examples/sample_las_top_view.html gulpfile.js
 examples/sample_las_top_view.html | 339 ++++++++++++++++++++++++++++++--------
 gulpfile.js                       |   2 +-
 2 files changed, 274 insertions(+), 67 deletions(-)
```

ソースコードとして変更されたファイルは次の2つです。

- `examples/sample_las_top_view.html`
- `gulpfile.js`

## `examples/sample_las_top_view.html` の変更

### 1. ローカル `.las` ファイル選択UIを追加

該当箇所:

- `examples/sample_las_top_view.html:172`

追加されたUI:

```html
<div id="local_file_controls">
  <label id="local_file_label" for="las_file_input">Local LAS file</label>
  <input id="las_file_input" type="file" accept=".las,.LAS">
</div>
```

目的:

- ローカルPC上の `.las` をブラウザから選択できるようにする。
- 選択ファイルはサーバへアップロードせず、ブラウザ内で読み込む。

### 2. URLクエリ由来の `file=` / `labelMap=` をローカル限定に制限

該当箇所:

- `examples/sample_las_top_view.html:244`

追加・利用されている関数:

```js
function resolveLocalDataPath(name, fallback, extension){
  ...
  if (url.origin !== window.location.origin) {
    throw new Error(`${name} must stay on ${window.location.origin}. External URLs are not allowed.`);
  }

  if (!url.pathname.startsWith("/data/")) {
    throw new Error(`${name} must resolve under /data/.`);
  }

  if (!url.pathname.toLowerCase().endsWith(extension)) {
    throw new Error(`${name} must end with ${extension}.`);
  }
  ...
}
```

目的:

- `?file=https://...` や `?labelMap=https://...` のような外部URL指定を拒否する。
- `file=` は `/data/*.las`、`labelMap=` は `/data/*.xml` に制限する。

### 3. 数値クエリを上限付きでクランプ

該当箇所:

- `examples/sample_las_top_view.html:229`
- `examples/sample_las_top_view.html:287`

対象:

- `maxPoints`
- `maxReadPoints`
- `pointSize`
- `chunkPoints`

目的:

- URLクエリで極端に大きい値を指定されても、ブラウザが過剰にメモリ確保しないようにする。

### 4. XMLラベル表示をXSSに強い形に維持

該当箇所:

- `examples/sample_las_top_view.html:490`
- `examples/sample_las_top_view.html:735`

重要な実装:

```js
name.textContent = `${label.name} [${label.id}] `;
```

目的:

- XML由来のラベル名をHTMLとして解釈せず、文字列として表示する。
- `<script>` や `<img onerror=...>` のような文字列がラベル名に入っていても、HTMLとして実行されにくくする。

### 5. XMLラベル色を `#rgb` / `#rrggbb` に制限

該当箇所:

- `examples/sample_las_top_view.html:530`
- `examples/sample_las_top_view.html:774`
- `examples/sample_las_top_view.html:781`

目的:

- XML由来の `color` をそのまま Three.js やCSSに渡さない。
- 長大な `rgb(...)` や不正な色文字列によるDoS・表示崩れリスクを下げる。

### 6. ローカル `.las` を `File.stream()` で読み込む処理を追加

該当箇所:

- `examples/sample_las_top_view.html:959`

重要な実装:

```js
async function loadLasPointsFromFile(file, options){
  if (!file || typeof file.name !== "string" || !file.name.toLowerCase().endsWith(".las")) {
    throw new Error("Select a local .las file.");
  }
  if (!file.stream) {
    throw new Error("File streaming is not available in this browser.");
  }

  const sourceLabel = `local file: ${file.name}`;
  return loadLasPointStream(file.stream().getReader(), file.size, sourceLabel, options);
}
```

目的:

- 選択した `.las` をサーバへ送らず、ブラウザ内で読む。
- `fetch(file)`、アップロード、`URL.createObjectURL(file)` を使わない。

### 7. Potree description へ入れる文字列をエスケープ

該当箇所:

- `examples/sample_las_top_view.html:978`

重要な実装:

```js
viewer.setDescription(
  `Rendering ${escapeHTML(sourceLabel)}<br>` +
  `labelMap=${escapeHTML(labelMapPath)}<br>` +
  ...
);
```

目的:

- ファイル名やURL由来文字列がHTMLとして解釈されるリスクを下げる。

### 8. 2回目以降の読み込みで既存点群を削除

該当箇所:

- `examples/sample_las_top_view.html:1015`
- `examples/sample_las_top_view.html:1043`
- `examples/sample_las_top_view.html:1063`

目的:

- ローカル `.las` を複数回選択しても、前の点群や床面がシーンに積み上がらないようにする。
- 不要な geometry / material を `dispose()` してメモリ負荷を下げる。

### 9. 起動時の `data/sample.las` 自動読み込みを停止

該当箇所:

- `examples/sample_las_top_view.html:1174`

現在の起動時表示:

```js
setViewerDescription(currentSourceLabel);
setStatus("Select a local .las file to render.");
setLabelLegendMessage("No point cloud loaded. Select a local .las file.");
```

目的:

- ページを開いただけで点群データを読み込まない。
- ユーザーがローカル `.las` を選択したときだけ点群を解析・描画する。

## `gulpfile.js` の変更

該当箇所:

- `gulpfile.js:80`

現在の設定:

```js
gulp.task('webserver', gulp.series(async function() {
  server = connect.server({
    host: '127.0.0.1',
    port: 1234,
    https: false,
  });
}));
```

変更内容:

- `host: '127.0.0.1'` を明示。
- `port: 1234` を明示。
- 現在は `https: false`。

意味:

- `127.0.0.1` は loopback address なので、通常は同じPCからだけアクセスできます。
- `0.0.0.0` で待ち受ける設定ではありません。
- HTTP平文ですが、ローカルPC内だけで使う前提なら外部公開リスクの主因ではありません。

## 直近コミット単位のソースコード変更

```text
2ba24857 セキュリティを強化
  - examples/sample_las_top_view.html
  - file= / labelMap= のローカル制限
  - escapeHTML(...)
  - numeric query clamp

1dd1146f 点群を選択可能なように変更
  - examples/sample_las_top_view.html
  - ローカル .las file input
  - File.stream().getReader()
  - 既存点群の削除と再描画

31c96118 デフォルトの点群読み込みをなくした
  - examples/sample_las_top_view.html
  - 起動時に data/sample.las を自動ロードしない

777cdf27 http 配信に変更
  - gulpfile.js
  - 現在は host: '127.0.0.1', port: 1234, https: false
```

## `.gitignore` の確認

`.gitignore` の内容を確認しました。

重要な行:

```text
1  /build
5  node_modules
12 examples/index.html
15 /examples/page.html
16 /resources/icons/index.html
35 data/
```

### ソースコードを無視しているか

確認結果:

- `src/` を無視する設定はありません。
- `examples/sample_las_top_view.html` を無視する設定はありません。
- `gulpfile.js` を無視する設定はありません。
- `docs/` 全体を無視する設定はありません。
- `.git/info/exclude` もデフォルトコメントのみで、追加の無視設定はありません。

次の確認でも、ソースコード本体は ignore されていません。

```text
git check-ignore -v examples/sample_las_top_view.html gulpfile.js src/Potree.js
```

結果:

```text
出力なし
```

これは、これらのファイルが `.gitignore` によって無視されていないことを意味します。

### 無視されるもの

`data/` は無視されています。

確認:

```text
git check-ignore -v data/sample.las
.gitignore:35:data/ data/sample.las
```

意味:

- `data/sample.las` のような点群データはGit管理から除外されます。
- 新しく `data/` 配下に置いた `.las` / `.xml` も、通常はGitに出てきません。
- これは点群データやローカル入力データを誤ってコミットしにくくする設定です。

注意:

- `data/` 配下にソースコード相当のファイルを置くと、それも無視されます。
- ソースコードは `src/`、`examples/`、`libs/`、`docs/` など、Git管理される場所に置くべきです。

## 現在の未追跡ファイル

現在の未追跡ファイルはMarkdownだけです。

```text
?? docs/explanation/sample_las_top_view_current_security_review.md
?? docs/explanation/source_changes_and_gitignore_review.md
?? docs/explanation/verify_npm_start_loopback_bind.md
```

これらは `.gitignore` によって無視されていません。必要なら通常の `git add` で追加できます。

## まとめ

- ソースコード変更は `examples/sample_las_top_view.html` と `gulpfile.js` に入っています。
- 現在のワークツリーにはソースコードの未コミット差分はありません。
- `.gitignore` にソースコード全体を無視する設定はありません。
- `examples/sample_las_top_view.html`、`gulpfile.js`、`src/` は ignore されていません。
- `data/` は ignore されています。点群データをGitに入れないための設定です。
