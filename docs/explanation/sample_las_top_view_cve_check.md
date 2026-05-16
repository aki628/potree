# `examples/sample_las_top_view.html` 関連 CVE 調査

調査日: 2026-05-16

この文書は `examples/sample_las_top_view.html` の実行に関係するものだけを対象にします。対象は次の2種類です。

1. HTML がブラウザに直接読み込む vendored JavaScript / CSS
2. `npm start` でこの HTML を `localhost:1234` から配信するための Node 側依存

Potree 全体の未使用機能、ビルド専用ツール、別サンプルだけで使う依存は原則として対象外です。ただし `npm audit` で検出され、`npm start` や静的配信に近いものは別枠で記録します。

## 結論

`sample_las_top_view.html` に関係する範囲では、CVE が報告されている古いライブラリが含まれています。

特に注意するものは次です。

- `libs/jquery/jquery-3.1.1.min.js`
  - `CVE-2019-11358`
  - `CVE-2020-11022`
  - `CVE-2020-11023`
- `libs/jquery-ui/jquery-ui.min.js` v1.12.1
  - `CVE-2021-41182`
  - `CVE-2021-41183`
  - `CVE-2021-41184`
  - `CVE-2022-31160`
- `libs/three.js/build/three.module.js` r124
  - `CVE-2020-28496`
- `npm start` の静的配信経路
  - `serve-static` / `send` 経由で `CVE-2024-43800` / `CVE-2024-43799`

ただし、現在の `sample_las_top_view.html` の実装を見る限り、これらがただちに「点群データが外部に送られる」CVE ではありません。主な種類は XSS、Prototype Pollution、DoS、静的配信時のテンプレートインジェクションです。

## 対象ファイルとバージョン

`sample_las_top_view.html` が直接読み込む主なライブラリは次です。

| ファイル | 確認できたバージョン | 備考 |
|---|---:|---|
| `libs/jquery/jquery-3.1.1.min.js` | 3.1.1 | CVEあり |
| `libs/jquery-ui/jquery-ui.min.js` | 1.12.1 | CVEあり |
| `libs/spectrum/spectrum.js` | 1.8.0 | 今回の範囲で直接該当するCVEは確認できず |
| `libs/tween/tween.min.js` | 0.15.0 | 今回の範囲で直接該当するCVEは確認できず |
| `libs/d3/d3.js` | 3.5.5 | 今回の範囲で直接該当するCVEは確認できず |
| `libs/proj4/proj4.js` | 2.6.2 | 今回の範囲で直接該当するCVEは確認できず |
| `libs/openlayers3/ol.js` | 3.11.2 | 今回の範囲で直接該当するCVEは確認できず |
| `libs/i18next/i18next.js` | ファイル内に明示バージョンなし | 今回の範囲で直接該当するCVEは確認できず |
| `libs/jstree/jstree.js` | 3.3.8 | CVEではないが、3.3.7未満に非CVEの既知脆弱性あり。3.3.8は修正後 |
| `libs/three.js/build/three.module.js` | r124 / npm換算 0.124.x 相当 | CVEあり |
| `libs/plasio/js/laslaz.js` | 明示バージョンなし | 今回の範囲で直接該当するCVEは確認できず |

## ブラウザ側ライブラリのCVE

### jQuery 3.1.1

`libs/jquery/jquery-3.1.1.min.js` は jQuery 3.1.1 です。

| CVE | 該当理由 | 内容 | このサンプルでの見立て |
|---|---|---|---|
| `CVE-2019-11358` | jQuery before 3.4.0 | `jQuery.extend(true, ...)` の Prototype Pollution | `sample_las_top_view.html` 本体では `$.extend(true, untrusted)` のような処理は見つかっていません。ただし Potree GUI や追加コードで未信頼オブジェクトを deep merge するとリスクになります。 |
| `CVE-2020-11022` | jQuery 1.12.0 以上 3.5.0 未満 | 未信頼HTMLを `.html()` / `.append()` などへ渡すと XSS の可能性 | サンプルのラベル表示は主に `textContent` を使っており、ラベルXMLの `name` をそのまま `.html()` には入れていません。Potree GUI側には `.html()` 使用箇所があるため、未信頼HTMLを渡す改造をした場合は注意。 |
| `CVE-2020-11023` | jQuery 1.0.3 以上 3.5.0 未満 | `<option>` を含む未信頼HTMLをDOM操作に渡すと XSS の可能性 | サンプル本体で未信頼 `<option>` HTML を jQuery DOM 操作に渡す経路は見つかっていません。 |

根拠:

- NVD `CVE-2019-11358`: https://nvd.nist.gov/vuln/detail/CVE-2019-11358
- NVD `CVE-2020-11022`: https://nvd.nist.gov/vuln/detail/CVE-2020-11022
- NVD `CVE-2020-11023`: https://nvd.nist.gov/vuln/detail/CVE-2020-11023

### jQuery UI 1.12.1

`libs/jquery-ui/jquery-ui.min.js` は jQuery UI 1.12.1 です。

| CVE | 該当理由 | 内容 | このサンプルでの見立て |
|---|---|---|---|
| `CVE-2021-41182` | jQuery UI before 1.13.0 | Datepicker の `altField` に未信頼値を受けると XSS の可能性 | `sample_las_top_view.html` 本体では Datepicker を使っていません。 |
| `CVE-2021-41183` | jQuery UI before 1.13.0 | Datepicker の `*Text` オプションに未信頼値を受けると XSS の可能性 | `sample_las_top_view.html` 本体では Datepicker を使っていません。 |
| `CVE-2021-41184` | jQuery UI before 1.13.0 | `.position()` の `of` オプションに未信頼値を受けると XSS の可能性 | サンプル本体で未信頼値を `.position({ of: ... })` に渡す経路は見つかっていません。 |
| `CVE-2022-31160` | jQuery UI before 1.13.2 | checkboxradio refresh 時の XSS | `sample_las_top_view.html` 本体は通常の `<input type="checkbox">` を作っていますが、jQuery UI の checkboxradio widget は使っていません。 |

Potree GUI では `profile_window` に対して `draggable()` / `resizable()` を使います。これは jQuery UI 依存ですが、上記CVEの直接条件である Datepicker / checkboxradio / 未信頼 `position.of` とは一致しません。

根拠:

- NVD `CVE-2021-41182`: https://nvd.nist.gov/vuln/detail/CVE-2021-41182
- NVD `CVE-2021-41183`: https://nvd.nist.gov/vuln/detail/CVE-2021-41183
- NVD `CVE-2021-41184`: https://nvd.nist.gov/vuln/detail/CVE-2021-41184
- NVD `CVE-2022-31160`: https://nvd.nist.gov/vuln/detail/CVE-2022-31160

### Three.js r124

`libs/three.js/build/three.module.js` は `REVISION = '124'` です。npm の `three` では 0.124.x 相当と見なせます。

| CVE | 該当理由 | 内容 | このサンプルでの見立て |
|---|---|---|---|
| `CVE-2020-28496` | `three` before 0.125.0 | `THREE.Color` が極端に長い `rgb(...)` / `hsl(...)` 文字列を処理するとリソース消費が大きくなる DoS | サンプルはラベルXMLの `color` を `normalizeHexColor()` で `#rgb` / `#rrggbb` のみ許可し、それ以外は fallback にします。そのため、ラベルXML経由で長大な `rgb(...)` 文字列を `new THREE.Color(...)` に渡す経路は抑えられています。 |
| `CVE-2022-0177` | three before 0.137.0 として一時登録 | NVD上では rejected | 現在のNVDでは使用すべきCVEではありません。 |

根拠:

- NVD `CVE-2020-28496`: https://nvd.nist.gov/vuln/detail/CVE-2020-28496
- NVD `CVE-2022-0177`: https://nvd.nist.gov/vuln/detail/CVE-2022-0177

## CVEではないが補足すべきもの

### jsTree 3.3.8

`libs/jstree/jstree.js` は jsTree 3.3.8 です。

Snyk には `jstree` 3.3.7 未満の Arbitrary Code Injection が登録されていますが、CVE ID はありません。今回のファイルは 3.3.8 なので、この非CVE脆弱性の修正後バージョンです。

根拠:

- Snyk `SNYK-JS-JSTREE-72490`: https://security.snyk.io/vuln/SNYK-JS-JSTREE-72490

## `npm start` / 静的配信側のCVE

`npm start` は `gulp watch` を実行し、`gulpfile.js` の `webserver` タスクで `gulp-connect` を使って `localhost:1234` に静的ファイルを配信します。

`npm audit --json` の結果、プロジェクト全体では 31 件の脆弱性が検出されました。ただし、その多くは Gulp の監視・ビルド・CLI・Rollup などの開発時依存です。`sample_las_top_view.html` の配信に直接近いものは次です。

| パッケージ | 現在バージョン | 検出 | 内容 | このサンプルでの見立て |
|---|---:|---|---|---|
| `gulp-connect` | 5.7.0 | `send` 経由 | `send < 0.19.0` の `CVE-2024-43799` | 静的配信で使われる依存です。通常のローカル利用では影響範囲はローカルですが、`1234` を外部公開するとリスクが上がります。 |
| `serve-static` | 1.14.1 | `CVE-2024-43800` / `send` 経由 | template injection leading to XSS | `gulp-connect` の静的配信経路で使われます。外部公開時は注意。 |
| `send` | 0.16.2 | `CVE-2024-43799` | redirect テンプレート周辺の XSS | `serve-static` 経由で入ります。 |

根拠:

- GitHub Advisory `CVE-2024-43799` / `send`: https://github.com/advisories/GHSA-m6fv-jmcg-4jfg
- GitHub Advisory `CVE-2024-43800` / `serve-static`: https://github.com/advisories/GHSA-cm22-4g7w-348p

## `npm audit` で検出されたが、今回のサンプル実行リスクからは一段遠いもの

`npm audit` では次のような依存も検出されました。

- `gulp` / `chokidar` / `glob-watcher` / `micromatch` / `braces`
- `rollup`
- `json5`
- `minimist`
- `yargs-parser`
- `semver`
- `qs`
- その他 transitive dependency

これらは開発・監視・ビルド・CLI 引数処理の依存が中心です。`examples/sample_las_top_view.html` をブラウザで開いたときに点群データを処理するブラウザ実行経路とは別です。

ただし、`npm start` 自体を不特定多数に使わせる、外部から操作可能な開発環境にする、CIや公開サーバでそのまま使う、といった運用では無視できません。開発サーバを外部公開しない前提なら、ブラウザ経由の点群閲覧リスクとしては `jquery` / `jquery-ui` / `three` / `serve-static` / `send` を優先して見ればよいです。

## このサンプルでの実害条件

### 点群データの外部送信

今回確認したCVEは、点群データを自動的に外部へアップロードするタイプではありません。

点群データの外部送信・外部取得に関しては、CVEよりも次の設定の方が重要です。

- `?file=https://...` のように外部URLを指定しない。
- `?labelMap=https://...` のように外部URLを指定しない。
- `gulpfile.js` に `host: "0.0.0.0"` を追加しない。
- Docker / VM / WSL / Codespaces / SSH forwarding で `1234` を外部公開しない。

### XSS

XSS系CVEが問題になるのは、未信頼データをHTMLとしてDOMへ入れる場合です。

現在の `sample_las_top_view.html` では、ラベル名の表示に `textContent` を使っています。

```js
name.textContent = `${label.name} [${label.id}] `;
```

そのため、ラベルXMLの `name` にHTMLを入れても、そのままHTMLとして実行されにくい実装です。

ただし、今後 `label.name` や外部から取った文字列を `.html(...)`、`.append(htmlString)`、jQuery UI の Datepicker / checkboxradio / position option に渡す改造をすると、上記CVEの条件に近づきます。

### Three.js の DoS

`CVE-2020-28496` は `THREE.Color` に極端に長い `rgb(...)` / `hsl(...)` を渡すようなケースが中心です。

現在のサンプルはラベルXMLの色を `normalizeHexColor()` で `#rgb` / `#rrggbb` に限定しています。

```js
if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) { ... }
if (/^#[0-9a-fA-F]{3}$/.test(trimmed)) { ... }
return fallback;
```

このため、ラベルXMLから長大な色文字列を直接 `THREE.Color` に渡す経路は抑えられています。

## 推奨対応

優先度順です。

1. `jquery` を 3.5.0 以上、できれば現行安定版へ更新する。
2. `jquery-ui` を 1.13.2 以上へ更新する。
3. `three.js` を r125 / 0.125.0 以上へ更新する。互換性確認を考えると、Potree側の Three.js 依存とまとめて検証する。
4. `npm start` の外部公開を避ける。特に `host: "0.0.0.0"` と port forward を避ける。
5. 開発サーバ依存を更新する場合は、`gulp-connect` / `serve-static` / `send` の静的配信経路を優先して確認する。
6. ラベルXMLやURLクエリなど、外部入力由来の文字列をHTMLとして挿入しない。現在の `textContent` 方針を維持する。

## 参考にした公開情報

- NVD `CVE-2019-11358`: https://nvd.nist.gov/vuln/detail/CVE-2019-11358
- NVD `CVE-2020-11022`: https://nvd.nist.gov/vuln/detail/CVE-2020-11022
- NVD `CVE-2020-11023`: https://nvd.nist.gov/vuln/detail/CVE-2020-11023
- NVD `CVE-2021-41182`: https://nvd.nist.gov/vuln/detail/CVE-2021-41182
- NVD `CVE-2021-41183`: https://nvd.nist.gov/vuln/detail/CVE-2021-41183
- NVD `CVE-2021-41184`: https://nvd.nist.gov/vuln/detail/CVE-2021-41184
- NVD `CVE-2022-31160`: https://nvd.nist.gov/vuln/detail/CVE-2022-31160
- NVD `CVE-2020-28496`: https://nvd.nist.gov/vuln/detail/CVE-2020-28496
- NVD `CVE-2022-0177`: https://nvd.nist.gov/vuln/detail/CVE-2022-0177
- GitHub Advisory `CVE-2024-43799`: https://github.com/advisories/GHSA-m6fv-jmcg-4jfg
- GitHub Advisory `CVE-2024-43800`: https://github.com/advisories/GHSA-cm22-4g7w-348p
- Snyk jsTree advisory without CVE: https://security.snyk.io/vuln/SNYK-JS-JSTREE-72490

