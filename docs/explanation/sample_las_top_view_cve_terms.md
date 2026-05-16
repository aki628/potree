# `examples/sample_las_top_view.html` 関連 CVE と用語の具体説明

調査日: 2026-05-16

この文書は、`docs/explanation/sample_las_top_view_cve_check.md` の補足です。CVE番号だけでは分かりにくいので、各脆弱性が「何をされたら危ないのか」と、`examples/sample_las_top_view.html` での実際の危険度を説明します。

## まず結論

今回のCVEは、点群ファイルを自動で外部へアップロードする種類の脆弱性ではありません。

主なリスクは次です。

- XSS: 悪意あるHTML/JavaScriptが画面内で実行される。
- Prototype Pollution: JavaScriptの共通オブジェクトの性質が汚染され、別の処理が誤動作する。
- DoS: ブラウザやサーバが重くなる、止まる。
- Template Injection: サーバが作るHTMLテンプレートに未信頼文字列が混ざり、XSSにつながる。

`sample_las_top_view.html` では、ラベル名を `textContent` で表示し、色も `#rgb` / `#rrggbb` に限定しています。そのため、現在の実装だけを見ると、CVEの危険条件に直接入る箇所は限定的です。

ただし、古いライブラリを読み込んでいる事実は残ります。今後、外部XML、URLクエリ、点群メタデータ、ユーザー入力を `.html()` や jQuery UI widget に渡す改造をすると、危険条件に近づきます。

## 用語説明

### CVE

CVE は公開された脆弱性に付く共通IDです。例: `CVE-2020-11022`。

重要なのは、CVEがあるから必ず攻撃される、という意味ではないことです。実際に危ないかは、該当バージョンを使っているか、脆弱なAPIを使っているか、外部入力がそこへ届くかで決まります。

### XSS

XSS は Cross-Site Scripting の略です。Webページに攻撃者のJavaScriptが混ざって実行される問題です。

このサンプルで例えると、もしラベルXMLの `name` に次のような文字列が入っていたとします。

```xml
<Label id="1" name="<img src=x onerror=alert(1)>"/>
```

この文字列を `.html(label.name)` のようにHTMLとして画面に入れると、ブラウザがタグとして解釈し、JavaScriptが実行される可能性があります。

一方、現在の `sample_las_top_view.html` は次のように `textContent` を使っています。

```js
name.textContent = `${label.name} [${label.id}] `;
```

`textContent` はHTMLとして解釈せず、ただの文字として表示します。そのため、この部分はXSSに強い実装です。

### Prototype Pollution

Prototype Pollution は、JavaScriptの全オブジェクトに共通する元になる部分を汚染する問題です。

JavaScriptでは多くのオブジェクトが `Object.prototype` を共有しています。もし外部入力に含まれる `__proto__` のような特別なキーを、深いマージ処理でそのまま取り込むと、全体に影響する性質を勝手に追加される可能性があります。

危険な形の例です。

```js
$.extend(true, {}, JSON.parse(untrustedJson));
```

`untrustedJson` に `{"__proto__": {"isAdmin": true}}` のような値が入ると、別の処理が `obj.isAdmin` を見たときに想定外の値が見える可能性があります。

現在の `sample_las_top_view.html` 本体では、未信頼データを `$.extend(true, ...)` に渡す経路は見つかっていません。

### DoS

DoS は Denial of Service の略です。サービス停止、または利用不能になる状態です。

ブラウザ側では、極端に長い文字列や巨大データを処理させてタブを固めるような形があります。サーバ側では、重い正規表現や大量リクエストでCPUやメモリを消費させる形があります。

今回の Three.js のCVEは、色文字列処理でブラウザやNodeプロセスを重くできるタイプです。

### Template Injection

Template Injection は、HTMLテンプレートを作る処理に未信頼入力が混ざり、想定外のHTMLやJavaScriptが出力される問題です。

今回の `serve-static` / `send` のCVEは、静的配信時のリダイレクトなどで作られるHTMLに未信頼入力が混ざるとXSSにつながる、という種類です。

`sample_las_top_view.html` の点群描画処理そのものではなく、`npm start` で立ち上げる開発サーバ側の問題です。

### CVSS

CVSS は脆弱性の深刻度スコアです。数値が高いほど一般的には深刻です。

ただし、CVSSは「一般的な条件」での深刻度です。このサンプルのように `localhost` だけで使う場合と、`0.0.0.0` やポートフォワードで外部公開する場合では、実際のリスクが変わります。

## 各CVEの具体説明

### `CVE-2019-11358`: jQuery Prototype Pollution

対象:

- `libs/jquery/jquery-3.1.1.min.js`
- jQuery 3.1.1 は jQuery 3.4.0 より前なので該当します。

何が危ないか:

- `jQuery.extend(true, {}, source)` のような深いコピーで、未信頼オブジェクトに `__proto__` が含まれていると、`Object.prototype` が汚染される可能性があります。
- 汚染後、別のコードが普通のオブジェクトを見たときに、攻撃者が足したプロパティが存在するように見えることがあります。

このサンプルでの条件:

- `sample_las_top_view.html` 本体では、ラベルXMLやURLクエリを `$.extend(true, ...)` に渡していません。
- したがって、現在のサンプル本体だけでは発火条件は見つかっていません。
- ただし、今後「ラベル設定JSONを読み込んで `$.extend(true, defaultConfig, userConfig)` で統合する」ような改造をすると危険になります。

対策:

- jQuery 3.4.0 以上、できればより新しい安定版へ更新する。
- 未信頼JSONを deep merge しない。
- `__proto__`、`constructor`、`prototype` などのキーを除外する。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2019-11358

### `CVE-2020-11022`: jQuery DOM操作 XSS

対象:

- `libs/jquery/jquery-3.1.1.min.js`
- jQuery 3.1.1 は jQuery 3.5.0 より前なので該当します。

何が危ないか:

- 未信頼HTML文字列を `.html()`、`.append()` などの jQuery DOM 操作へ渡すと、JavaScriptが実行される可能性があります。
- NVDでは、サニタイズ後でも問題が起こり得ると説明されています。

このサンプルでの条件:

- ラベルXMLの `name` は `textContent` で表示されており、HTMLとして解釈されません。
- そのため、ラベル名経由の典型的なXSS条件は抑えられています。
- ただし、今後 `labelLegendBody.innerHTML += label.name` や `$(...).html(label.name)` のように変えると危険です。

危険な改造例:

```js
$(".label_name").html(label.name);
```

安全寄りの書き方:

```js
element.textContent = label.name;
```

対策:

- jQuery 3.5.0 以上へ更新する。
- 外部入力をHTMLとして入れない。
- 表示テキストは `textContent` を使う。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2020-11022

### `CVE-2020-11023`: jQuery `<option>` 関連 XSS

対象:

- `libs/jquery/jquery-3.1.1.min.js`
- jQuery 3.1.1 は jQuery 3.5.0 より前なので該当します。

何が危ないか:

- `<option>` を含む未信頼HTMLを `.html()` や `.append()` などへ渡すと、JavaScript実行につながる可能性があります。

このサンプルでの条件:

- `sample_las_top_view.html` 本体では `<select>` や `<option>` を外部入力から生成していません。
- ラベル操作も checkbox と button を `document.createElement()` で作っています。
- そのため、現在のサンプル本体ではこのCVEの直接条件は見つかっていません。

危険な改造例:

```js
$("#label_select").append(labelXmlProvidedOptionHtml);
```

安全寄りの書き方:

```js
const option = document.createElement("option");
option.textContent = label.name;
select.appendChild(option);
```

対策:

- jQuery 3.5.0 以上へ更新する。
- `<option>` を文字列HTMLとして作らない。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2020-11023

### `CVE-2021-41182`: jQuery UI Datepicker `altField` XSS

対象:

- `libs/jquery-ui/jquery-ui.min.js`
- jQuery UI 1.12.1 は 1.13.0 より前なので該当します。

何が危ないか:

- Datepicker widget の `altField` オプションに未信頼文字列を渡すと、JavaScript実行につながる可能性があります。
- `altField` は、選択した日付を別の入力欄にも反映するための指定です。

このサンプルでの条件:

- `sample_las_top_view.html` 本体では Datepicker を使っていません。
- Potree GUI で使っている jQuery UI は主に `draggable()` / `resizable()` です。
- そのため、このサンプルの通常操作では直接発火しません。

危険な改造例:

```js
$("#date").datepicker({
  altField: new URLSearchParams(location.search).get("field")
});
```

対策:

- jQuery UI 1.13.0 以上へ更新する。
- Datepicker の `altField` をURLクエリや外部JSONから受け取らない。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2021-41182

### `CVE-2021-41183`: jQuery UI Datepicker `*Text` XSS

対象:

- `libs/jquery-ui/jquery-ui.min.js`
- jQuery UI 1.12.1 は 1.13.0 より前なので該当します。

何が危ないか:

- Datepicker の `prevText`、`nextText`、`currentText` などの `*Text` オプションに未信頼文字列を渡すと、HTMLとして扱われてJavaScript実行につながる可能性があります。

このサンプルでの条件:

- `sample_las_top_view.html` 本体では Datepicker を使っていません。
- 通常操作では直接関係しません。

危険な改造例:

```js
$("#date").datepicker({
  prevText: externalConfig.prevText
});
```

対策:

- jQuery UI 1.13.0 以上へ更新する。
- UIラベル文字列をHTMLとして扱わない。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2021-41183

### `CVE-2021-41184`: jQuery UI `.position({ of: ... })` XSS

対象:

- `libs/jquery-ui/jquery-ui.min.js`
- jQuery UI 1.12.1 は 1.13.0 より前なので該当します。

何が危ないか:

- jQuery UI の `.position()` utility の `of` オプションに未信頼文字列を渡すと、JavaScript実行につながる可能性があります。
- `of` は「どの要素を基準に位置決めするか」を指定するオプションです。

このサンプルでの条件:

- `sample_las_top_view.html` 本体では、未信頼値を `.position({ of: ... })` に渡していません。
- Potree GUI の `draggable()` / `resizable()` 利用とは、このCVEの直接条件が異なります。

危険な改造例:

```js
$("#panel").position({
  of: new URLSearchParams(location.search).get("target")
});
```

対策:

- jQuery UI 1.13.0 以上へ更新する。
- `of` にはDOM要素や固定のCSSセレクタだけを渡す。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2021-41184

### `CVE-2022-31160`: jQuery UI checkboxradio XSS

対象:

- `libs/jquery-ui/jquery-ui.min.js`
- jQuery UI 1.12.1 は 1.13.2 より前なので該当します。

何が危ないか:

- `checkboxradio` widget を使い、`label` 内に input があり、そのラベル内容にエンコード済みHTMLが含まれる場合、`.checkboxradio("refresh")` 時にHTMLエンティティが誤ってデコードされ、JavaScript実行につながる可能性があります。

このサンプルでの条件:

- `sample_las_top_view.html` は checkbox を作っていますが、jQuery UI の `checkboxradio()` widget は使っていません。
- ラベル名も `textContent` で入れています。
- そのため、現在のサンプル本体では直接発火しません。

危険な改造例:

```js
$("input[type=checkbox]").checkboxradio();
$("input[type=checkbox]").checkboxradio("refresh");
```

このとき、初期HTMLの `label` 内容を外部入力で作っていると危険条件に近づきます。

対策:

- jQuery UI 1.13.2 以上へ更新する。
- checkboxradio widget を使う場合、ラベルHTMLを外部入力から作らない。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2022-31160

### `CVE-2020-28496`: Three.js `Color` のリソース消費

対象:

- `libs/three.js/build/three.module.js`
- `REVISION = '124'`
- three 0.125.0 より前なので該当します。

何が危ないか:

- `THREE.Color` が `rgb(...)` や `hsl(...)` のような色文字列を処理するとき、極端に長い文字列を渡されると処理が重くなる可能性があります。
- これはXSSではなく、DoS系です。つまり、コード実行よりも「重くなる」「固まる」方向の問題です。

このサンプルでの条件:

- ラベルXMLから読む `color` は `normalizeHexColor()` を通ります。
- 許可されるのは `#rgb` と `#rrggbb` だけです。
- `rgb(     ...` のような長い文字列は fallback されます。
- そのため、ラベルXML経由でこのCVEを踏む可能性は低いです。

該当する安全処理:

```js
if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) { ... }
if (/^#[0-9a-fA-F]{3}$/.test(trimmed)) { ... }
return fallback;
```

危険な改造例:

```js
material.color = new THREE.Color(node.getAttribute("color"));
```

このように、XMLの `color` を検証せず直接 `THREE.Color` に渡すと危険条件に近づきます。

対策:

- Three.js r125 / 0.125.0 以上へ更新する。
- 色入力は今のようにホワイトリスト方式で検証する。

根拠:

- NVD: https://nvd.nist.gov/vuln/detail/CVE-2020-28496

### `CVE-2024-43799`: `send` の template injection / XSS

対象:

- `node_modules/send` 0.16.2
- `gulp-connect` / `serve-static` 経由で静的配信に使われます。

何が危ないか:

- `send` のリダイレクト用HTMLテンプレートに未信頼入力が混ざると、XSSにつながる可能性があります。
- GitHub Advisory では、`SendStream.redirect()` に未信頼入力を渡す場合が問題条件として説明されています。

このサンプルでの条件:

- `sample_las_top_view.html` のブラウザ内点群処理ではなく、`npm start` で立つ開発サーバ側の問題です。
- 通常の `localhost` 利用では攻撃面は自分のPC内に限られます。
- `1234` を外部公開すると、第三者が開発サーバへリクエストできるため、リスクが上がります。

対策:

- `send` 0.19.0 以上を使う依存構成へ更新する。
- 開発サーバを外部公開しない。
- `gulpfile.js` に `host: "0.0.0.0"` を追加しない。

根拠:

- GitHub Advisory: https://github.com/advisories/GHSA-m6fv-jmcg-4jfg

### `CVE-2024-43800`: `serve-static` の template injection / XSS

対象:

- `node_modules/serve-static` 1.14.1
- `gulp-connect` が静的ファイル配信で使います。

何が危ないか:

- `serve-static` のリダイレクト処理で、未信頼入力がテンプレートに混ざるとXSSにつながる可能性があります。
- GitHub Advisory では、`redirect()` に未信頼入力を渡す場合が問題条件として説明されています。

このサンプルでの条件:

- 点群描画コードの問題ではなく、開発サーバの静的配信経路の問題です。
- `localhost` だけなら影響範囲は限定的です。
- 外部公開時は、第三者から細工したURLを投げられる可能性が出ます。

対策:

- `serve-static` 1.16.0 以上を使う依存構成へ更新する。
- 開発サーバを外部公開しない。

根拠:

- GitHub Advisory: https://github.com/advisories/GHSA-cm22-4g7w-348p

## CVEではないが注意したもの

### jsTree 3.3.8

`libs/jstree/jstree.js` は 3.3.8 です。

Snyk には `jstree` 3.3.7 未満の Arbitrary Code Injection が登録されています。これはCVE IDがありません。原因は `eval()` の不適切な使用です。

今回のファイルは 3.3.8 なので、Snykが示す `<3.3.7` には該当しません。

根拠:

- Snyk: https://security.snyk.io/vuln/SNYK-JS-JSTREE-72490

## このサンプルで特に守るべきこと

1. ラベル名やURL由来文字列を `.html()` / `.append(htmlString)` に渡さない。
2. 今の `textContent` 方針を維持する。
3. ラベル色の `normalizeHexColor()` を外さない。
4. jQuery / jQuery UI / Three.js を更新する場合は、Potree GUI の動作確認もセットで行う。
5. `npm start` の `localhost:1234` を外部公開しない。
6. `file=` / `labelMap=` に外部URLを指定して検証するときは、取得先サーバにアクセス情報が残ることを前提にする。

## 参考資料

- NVD `CVE-2019-11358`: https://nvd.nist.gov/vuln/detail/CVE-2019-11358
- NVD `CVE-2020-11022`: https://nvd.nist.gov/vuln/detail/CVE-2020-11022
- NVD `CVE-2020-11023`: https://nvd.nist.gov/vuln/detail/CVE-2020-11023
- NVD `CVE-2021-41182`: https://nvd.nist.gov/vuln/detail/CVE-2021-41182
- NVD `CVE-2021-41183`: https://nvd.nist.gov/vuln/detail/CVE-2021-41183
- NVD `CVE-2021-41184`: https://nvd.nist.gov/vuln/detail/CVE-2021-41184
- NVD `CVE-2022-31160`: https://nvd.nist.gov/vuln/detail/CVE-2022-31160
- NVD `CVE-2020-28496`: https://nvd.nist.gov/vuln/detail/CVE-2020-28496
- GitHub Advisory `CVE-2024-43799`: https://github.com/advisories/GHSA-m6fv-jmcg-4jfg
- GitHub Advisory `CVE-2024-43800`: https://github.com/advisories/GHSA-cm22-4g7w-348p
- Snyk `SNYK-JS-JSTREE-72490`: https://security.snyk.io/vuln/SNYK-JS-JSTREE-72490

