# `sample_las_top_view.html` セキュリティ修正まとめ

作成日: 2026-05-16

対象ファイル:

- `examples/sample_las_top_view.html`
- `docs/adr/0006-harden-sample-las-query-inputs.md`

## 目的

`docs/explanation` にまとめたセキュリティ調査を踏まえて、`examples/sample_las_top_view.html` の実装を安全側に寄せました。

主に対応したリスクは次です。

- `file=` / `labelMap=` に外部URLを指定できるリスク
- URLクエリ由来の文字列が `viewer.setDescription(...)` 経由でHTMLとして挿入されるリスク
- `chunkPoints` などの数値クエリに極端な値を入れてブラウザのメモリ使用量を増やせるリスク
- ラベル名や色の扱いを安全なまま維持すること

## 追加したADR

次のADRを追加しました。

```text
docs/adr/0006-harden-sample-las-query-inputs.md
```

ADRには以下を記載しています。

- 背景
- 採用した方針
- 影響
- 完了条件
- 実際の検証結果

## 実装変更の概要

### 1. `file=` / `labelMap=` の検証を追加

以前はURLクエリからそのまま値を取得していました。

```js
const samplePath = params.get("file") || "../data/sample.las";
const labelMapPath = params.get("labelMap") || "../data/sample_labels.xml";
```

修正後は `resolveLocalDataPath(...)` を通して検証します。

```js
samplePath = resolveLocalDataPath("file", defaultSamplePath, ".las");
labelMapPath = resolveLocalDataPath("labelMap", defaultLabelMapPath, ".xml");
```

この関数では次を確認します。

- URLとして解釈できること
- 現在のオリジンと同じであること
- `/data/` 配下であること
- `file=` は `.las` で終わること
- `labelMap=` は `.xml` で終わること
- クエリ文字列やフラグメントを含まないこと

これにより、次のような指定は拒否されます。

```text
?file=https://example.com/sample.las
?labelMap=https://example.com/labels.xml
?file=../examples/sample_las_top_view.html
?labelMap=/data/sample_labels.xml?<script>
```

## 2. 外部URL指定を禁止

`file=` / `labelMap=` について、外部オリジンのURLを拒否するようにしました。

```js
if (url.origin !== window.location.origin) {
  throw new Error(`${name} must stay on ${window.location.origin}. External URLs are not allowed.`);
}
```

これにより、このサンプルは任意の外部URLを読むローダーではなく、ローカルの `/data/` 配下を読むデモとして動作します。

## 3. `viewer.setDescription(...)` のXSS対策

Potree の `viewer.setDescription(...)` は内部で `.html(...)` を使います。

そのため、URLクエリ由来の文字列をそのまま渡すと、HTMLとして解釈される可能性がありました。

修正後は `escapeHTML(...)` を追加し、`samplePath` と `labelMapPath` をエスケープしてから渡しています。

```js
viewer.setDescription(
  `Rendering ${escapeHTML(samplePath)}<br>` +
  `labelMap=${escapeHTML(labelMapPath)}<br>` +
  ...
);
```

これにより、仮に危険な文字列が入り込んでも、HTMLタグとして解釈されにくくなります。

## 4. 数値クエリの上限・下限を追加

以前は `chunkPoints` などに極端な値を入れられる余地がありました。

修正後は `parseBoundedQueryNumber(...)` で範囲を制限します。

```js
pointLimit = parseBoundedQueryNumber("maxPoints", 0, 0, 20_000_000, true);
readLimit = parseBoundedQueryNumber("maxReadPoints", 0, 0, 200_000_000, true);
pointSize = parseBoundedQueryNumber("pointSize", 0.015, 0.001, 1);
chunkPoints = parseBoundedQueryNumber("chunkPoints", 1_000_000, 50_000, 2_000_000, true);
```

これにより、極端な値でブラウザに大きなメモリ確保をさせるリスクを下げています。

## 5. ラベル名表示は `textContent` のまま維持

ラベルXMLから読み取ったラベル名は、引き続き `textContent` で表示します。

```js
name.textContent = `${label.name} [${label.id}] `;
```

`textContent` は文字列をHTMLとして解釈しません。

そのため、ラベル名に次のような文字列が入っていても、HTMLタグとして実行されにくいです。

```xml
<Label id="1" name="<img src=x onerror=alert(1)>"/>
```

## 6. ラベル色の検証は維持

ラベルXMLの `color` は、引き続き `normalizeHexColor(...)` を通します。

許可される形式は次だけです。

- `#rgb`
- `#rrggbb`

それ以外は fallback 色になります。

これにより、Three.js の `Color` に極端に長い `rgb(...)` / `hsl(...)` 文字列を渡すリスクを下げています。

## 検証内容

次を確認しました。

- `examples/sample_las_top_view.html` に `resolveLocalDataPath(...)` が追加されていること
- `file=` / `labelMap=` が外部オリジンを拒否すること
- `/data/` 配下のみ許可する実装になっていること
- `file=` は `.las` のみ、`labelMap=` は `.xml` のみ許可すること
- `viewer.setDescription(...)` に `escapeHTML(samplePath)` / `escapeHTML(labelMapPath)` を渡していること
- ラベル名表示が `textContent` のままであること
- ラベル色が `normalizeHexColor(...)` を通ること
- 数値クエリが `parseBoundedQueryNumber(...)` を通ること
- インライン module script の構文が壊れていないこと
- `npm start` で HTTPS サーバが起動すること
- `https://127.0.0.1:1234/examples/sample_las_top_view.html` が取得できること
- `https://127.0.0.1:1234/data/sample.las` が取得できること
- `https://127.0.0.1:1234/data/sample_labels.xml` が取得できること
- `gulpfile.js` は `127.0.0.1` bind のままで、`0.0.0.0` は追加していないこと

検証後、起動していたHTTPS開発サーバは停止済みです。

## 残る注意点

この修正は `sample_las_top_view.html` を安全側に寄せるものです。

ただし、次は引き続き注意が必要です。

- `npm start` のポート `1234` を外部公開しない。
- Docker / VM / WSL / Codespaces / SSH port forwarding で `1234` を公開しない。
- 外部データセットを読みたい場合は、このサンプルを緩めるのではなく、認証・CORS・公開範囲を別途設計した専用サンプルを作る。
- jQuery / jQuery UI / Three.js などの古いライブラリ自体のCVEは、依存更新で別途対応する必要がある。

