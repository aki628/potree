# `examples/sample_las_top_view.html` 操作時のセキュリティ確認

調査日: 2026-05-16

## 結論

現状の `examples/sample_las_top_view.html` を通常どおりローカルPC上で操作する範囲では、選択したローカル `.las` 点群ファイルが自動で外部へ送信されたり、外部から直接アクセスできるようになったりする実装にはなっていません。

主な理由は次です。

- ローカル `.las` は `<input type="file">` で選択し、ブラウザの `File.stream().getReader()` で読みます。
- 選択した `.las` を `fetch(...)` に渡していません。
- 選択した `.las` をサーバへアップロードする処理はありません。
- `URL.createObjectURL(...)` を使っていないため、選択ファイル用の参照URLも作っていません。
- 起動時に `data/sample.las` を自動読み込みしません。
- `file=` / `labelMap=` のURLクエリは `resolveLocalDataPath(...)` で同一オリジンかつ `/data/` 配下に制限されています。
- 開発サーバは `gulpfile.js` 上で `host: '127.0.0.1'` に固定されており、`0.0.0.0` では待ち受けていません。

したがって、通常利用時の主要な注意点は次の2つです。

1. `npm start` の `1234` ポートを Docker / WSL portproxy / SSH port forwarding などで外部公開しない。
2. 出所不明または細工された `.las` / `.xml` を読み込まない。

## 確認対象

- `examples/sample_las_top_view.html`
- `gulpfile.js`
- 関連既存ドキュメント:
  - `docs/adr/0006-harden-sample-las-query-inputs.md`
  - `docs/adr/0007-local-las-file-selection.md`
  - `docs/explanation/sample_las_malicious_input_examples.md`
  - `docs/explanation/sample_las_top_view_cve_terms.md`

## 通信経路の確認

### ローカル `.las` 選択

ローカルファイル選択UIは次です。

```html
<input id="las_file_input" type="file" accept=".las,.LAS">
```

選択後の読み込みは次の関数です。

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

この経路では、選択した `.las` はブラウザ内の `File` オブジェクトからストリームで読まれます。サーバへアップロードする処理、外部URLへ送る処理、オブジェクトURL化する処理はありません。

### `fetch(...)` の残存箇所

現状の `fetch(...)` は2箇所です。

1. `loadLabelDefinitions(url)`
   - ラベル定義XMLを読むための `fetch(url)`。
   - `url` は `labelMapPath` です。
   - `labelMapPath` は `resolveLocalDataPath("labelMap", ..., ".xml")` を通るため、外部URLは拒否されます。

2. `loadLasPoints(url, options)`
   - `/data/*.las` URLを読むための関数。
   - 現状の起動時処理では `loadLasPoints(samplePath, ...)` を呼んでいません。
   - ローカルファイル選択時もこの関数は使わず、`loadLasPointsFromFile(...)` を使います。

つまり、通常の操作で選択したローカル `.las` は `fetch(...)` の対象になりません。

## 外部送信リスク

### 選択したローカル `.las`

現状の実装では、選択したローカル `.las` が外部へ送信される経路は見つかりません。

確認した不存在の処理:

- `fetch(file)` のような処理
- `XMLHttpRequest` によるアップロード
- `navigator.sendBeacon(...)`
- `WebSocket`
- `URL.createObjectURL(file)`
- `<form>` によるアップロード
- `Potree.loadPointCloud(...)` による外部点群ロード

### ラベルXML

ラベルXMLは `labelMap=` クエリで指定できますが、現在は次の制限があります。

- 同一オリジンであること
- `/data/` 配下であること
- `.xml` で終わること
- query string / fragment を含まないこと

そのため、次のような外部URLは拒否されます。

```text
?labelMap=https://example.com/labels.xml
```

## 外部からアクセスされるリスク

`gulpfile.js` の開発サーバ設定は現在次です。

```js
connect.server({
  host: '127.0.0.1',
  port: 1234,
  https: false,
});
```

`host: '127.0.0.1'` なので、通常は同じPCからのアクセスに限定されます。`0.0.0.0` のようにLANや外部ネットワーク向けに待ち受ける設定ではありません。

ただし、次のような外部公開設定を別途行うと、`1234` に外部からアクセスできる可能性があります。

- Docker の `-p 0.0.0.0:1234:1234`
- WSL の `netsh interface portproxy` で `listenaddress=0.0.0.0 listenport=1234`
- SSH の `-R 0.0.0.0:1234:127.0.0.1:1234`
- Codespaces やクラウドIDEでポートを Public にする
- ルータやファイアウォールで `1234` を公開する

この場合でも、ファイル選択で選んだローカル `.las` はサーバに置かれないため、外部から直接取得できません。一方で、リポジトリ配下で静的配信されるファイルは見える可能性があります。

## HTTPSについて

現在の `gulpfile.js` は `https: false` です。

これは、通常の `127.0.0.1` ローカル操作では外部公開リスクの主因ではありません。ただし、通信内容はHTTPの平文です。ローカルPC内だけで使う前提なら影響は限定的ですが、外部公開や共有ネットワーク越しの利用には向きません。

安全性を説明する場合は、次のように分けるのが正確です。

- 外部からアクセスできるか: `host: '127.0.0.1'` なので通常は外部から見えない。
- 通信が暗号化されているか: 現状は `https: false` なので暗号化されていない。
- 選択した `.las` が送信されるか: 送信されない。

## XSS観点

### ラベル名

XML由来のラベル名は表示時に `textContent` を使っています。

```js
name.textContent = `${label.name} [${label.id}] `;
```

`textContent` はHTMLとして解釈せず、文字列として表示します。そのため、XMLに次のようなラベル名が含まれていても、現状の表示経路ではHTMLとして実行されません。

```xml
<Label id="2" name="<img src=x onerror=alert(1)>" color="#d2b48c" />
```

### Potree description

Potree description はHTMLとして描画される可能性があるため、文字列を `escapeHTML(...)` に通しています。

```js
viewer.setDescription(
  `Rendering ${escapeHTML(sourceLabel)}<br>` +
  `labelMap=${escapeHTML(labelMapPath)}<br>` +
  ...
);
```

これにより、ファイル名やURL由来文字列に `<script>` などが入っていても、そのままHTMLとして解釈されにくくしています。

### 注意すべき変更

今後、次のような変更をするとXSSリスクが上がります。

```js
name.innerHTML = label.name;
```

```js
$(name).html(label.name);
```

```js
$("#label_legend_body").append(`<div>${label.name}</div>`);
```

```js
viewer.setDescription(`Rendering ${file.name}`);
```

ラベル名、ファイル名、URLクエリ由来の文字列は、今後も `textContent` または `escapeHTML(...)` 経由で扱うべきです。

## 悪意ある `.las` / `.xml` を使った場合のリスク

外部送信とは別に、悪意ある入力ファイルによるブラウザ側リスクは残ります。

具体例:

- XMLの `name` にHTML/JavaScript風文字列を入れる
- XMLの `color` に極端に長い `rgb(...)` や不正な値を入れる
- XMLを極端に巨大化する
- LASヘッダを壊す
- 点数、レコード長、座標範囲を異常値にする
- 対応外または矛盾した point format を指定する

起こり得る問題:

- ブラウザのフリーズ
- メモリ大量消費
- ページクラッシュ
- 表示崩れ
- 古いライブラリの脆弱性を突く攻撃の誘発

現状の対策:

- ラベル名は `textContent`
- ラベル色は `normalizeHexColor(...)` で `#rgb` / `#rrggbb` に限定
- XMLの `id` は `0` から `255` の整数に限定
- LASの `LASF` シグネチャを確認
- 対応外 point format はエラー
- `maxPoints` / `maxReadPoints` / `chunkPoints` / `pointSize` をクランプ

ただし、すべての異常LASを完全に安全化するものではありません。出所が分かっている `.las` / `.xml` だけを使う運用が必要です。

## 現状の安全性評価

| 観点 | 評価 | 根拠 |
| --- | --- | --- |
| 選択した `.las` の外部送信 | 低リスク | `File.stream().getReader()` でブラウザ内読み込み。アップロード処理なし |
| 選択した `.las` への外部アクセス | 低リスク | サーバ配下に置かず、オブジェクトURLも作らない |
| 起動時の点群自動読み込み | 低リスク | `data/sample.las` を自動読み込みしない |
| `file=` / `labelMap=` による外部URLアクセス | 低リスク | `resolveLocalDataPath(...)` で外部originを拒否 |
| 外部PCからページへアクセス | 通常は低リスク | `host: '127.0.0.1'`。ただし別途ポート公開した場合は別 |
| XSS | 低から中 | 現状は `textContent` / `escapeHTML(...)`。ただし古いjQuery系ライブラリがあるため改造時は注意 |
| 悪意あるLAS/XMLによるDoS | 中 | ブラウザで解析するため、巨大・壊れた入力は負荷やクラッシュの原因になる |
| 通信暗号化 | 低 | 現状 `https: false`。ローカル限定前提なら影響限定的だが、外部公開には不向き |

## 運用ルール

1. `npm start` はローカルPCでのみ使う。
2. `gulpfile.js` の `host: '127.0.0.1'` を維持し、`0.0.0.0` にしない。
3. Docker / WSL / SSH / Codespaces などで `1234` を外部公開しない。
4. 出所不明の `.las` / `.xml` を読み込まない。
5. ラベル名やファイル名を `innerHTML` / `.html()` / `.append(htmlString)` に渡さない。
6. `normalizeHexColor(...)` と `escapeHTML(...)` を外さない。
7. 巨大なLASは `maxPoints` / `maxReadPoints` を設定して段階的に確認する。

## 説明用の短い回答

> 現状の `examples/sample_las_top_view.html` は、ローカルで選択した `.las` を外部へ送信する実装ではありません。選択ファイルはブラウザの File API で読み込まれ、サーバへアップロードされず、外部から直接アクセスできるURLも作りません。また、開発サーバは `127.0.0.1:1234` で待ち受けるため、通常は同じPCからしかアクセスできません。ただし、Docker / WSL / SSH などで `1234` を外部公開した場合や、出所不明の `.las` / `.xml` を読み込んだ場合は、外部アクセス、ブラウザ負荷、クラッシュ、XSS系リスクが発生し得ます。
