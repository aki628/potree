# `examples/sample_las_top_view.html` で避けるべき悪意ある入力例

調査日: 2026-05-16

この文書は、`examples/sample_las_top_view.html` の安全性を説明するときに想定される質問、

- 「悪意のある `.xml` / `.las` とは具体的にどんなものか」
- 「それを読み込むと何が起きる可能性があるか」
- 「XSS の観点では何がまずいか」

に答えるためのメモです。

## 先に結論

現状の `examples/sample_las_top_view.html` は、ローカルPCから選択した `.las` を外部へアップロードしません。選択ファイルは `File.stream().getReader()` でブラウザ内だけで読みます。

今回の安全化で大きい点は、`.xml` から読んだラベル名や色を「そのままHTMLとして画面に差し込まない」ようにしたことです。ラベル名は `textContent` で文字として表示し、色は `normalizeHexColor(...)` で `#rgb` / `#rrggbb` だけに制限します。

ただし、ファイルをブラウザで解析する以上、信頼できない `.las` / `.xml` を読み込むと、ブラウザのフリーズ、メモリ不足、表示崩れ、古いライブラリの脆弱性を突く攻撃につながる可能性はあります。

そのため説明としては、次の言い方が適切です。

> このビューアは選択したローカル `.las` を外部に送信しない設計です。ただし、出所不明または細工された `.las` / `.xml` は、ブラウザで解析・描画する段階でフリーズ、メモリ大量消費、クラッシュ、またはXSS系脆弱性の誘発につながる可能性があります。信頼できるファイルだけを使用してください。

## 変更で何が安全になったか

悪意あるXMLで一番分かりやすい危険は、ラベル名にHTMLやJavaScript風の文字列を入れることです。

例えば、XMLに次のようなラベル名が入っていたとします。

```xml
<Label id="2" name="<img src=x onerror=alert(1)>" color="#d2b48c" visible="true" />
```

危ない実装では、この `name` をHTMLとして画面に入れてしまいます。

```js
labelNameElement.innerHTML = label.name;
```

この場合、ブラウザは `<img ...>` をただの文字ではなく画像タグとして解釈します。画像の読み込みに失敗すると `onerror` が動き、JavaScriptが実行される可能性があります。これがXSSです。

現在の実装では、ラベル名を次のように文字として入れます。

```js
name.textContent = `${label.name} [${label.id}] `;
```

`textContent` では `<img src=x onerror=alert(1)>` はタグになりません。画面にはそのまま文字として表示され、JavaScriptとして実行されません。

外部サイトへの勝手なアクセスも同じ考え方です。もしXMLのラベル名に次のような文字列が入っていて、

```xml
<Label id="4" name="<img src='https://evil.example/pixel'>" color="#ff0000" />
```

それをHTMLとして挿入すると、ブラウザは画像を取りに行こうとして `https://evil.example/pixel` へアクセスする可能性があります。現在のように `textContent` で表示すれば、これは画像タグではなく文字列になるため、この自動アクセスは起きません。

ただし、XML内の値をURLとして `fetch(...)` や `window.open(...)` に渡すような処理を追加した場合は別問題です。その場合は、文字表示を `textContent` にしていても、URLとして使う前に「同じサーバ配下だけ」「信頼済みドメインだけ」などの制限が必要です。

今回の防御を素人向けに言うと、次の通りです。

> 悪意あるXMLに「HTMLタグのふりをした文字」が入っていても、ビューア側ではそれをHTMLとして組み立てず、ただの文字として表示するようにした。さらに色の値も決まった形式だけに制限した。これにより、XMLのラベル名や色を入口にしてJavaScriptを実行させる典型的な攻撃を防ぎやすくなった。

さらに短く説明するなら、次の通りです。

> 読み込む `.xml` の `Label` のラベル名に、外部サイトへアクセスさせるHTML風の文字列が入っていると、危ない実装ではブラウザがそれを本物のHTMLとして解釈し、外部サイトへ勝手にアクセスする可能性がありました。現状はラベル名をHTMLではなく文字として表示するため、その経路を防ぐようにしています。ただし、安全のため出所不明の `.xml` ファイルは使わないでください。

## 悪意ある XML の具体例

`sample_las_top_view.html` の XML はラベル定義として使われます。主に `id`、`name`、`color`、`visible` を読みます。

### 1. ラベル名に HTML / JavaScript を入れる

まずい例:

```xml
<Label id="2" name="<img src=x onerror=alert(1)>" color="#d2b48c" visible="true" />
```

または:

```xml
<Label id="3" color="#7fc97f" visible="true">
  <script>alert(1)</script>
</Label>
```

何がまずいか:

- ラベル名を `.html(...)` や `innerHTML` に入れる実装だと、HTMLとして解釈され、XSSになる可能性があります。
- XSSになると、同じページ内で攻撃者のJavaScriptが実行されます。
- JavaScriptが実行されると、画面改ざん、ブラウザ内データの読み取り、別URLへの通信などにつながる可能性があります。

現状の対策:

- 現在のラベル表示は `textContent` を使っています。
- `textContent` は `<script>` や `<img onerror=...>` をHTMLとして実行せず、ただの文字として表示します。
- そのため、現状のラベル表示経路ではこの典型的なXSSは抑えられています。
- 悪意あるリンクや画像タグも、HTML要素として作られず文字として扱われます。

注意:

- 今後、ラベル名を `.html(label.name)`、`append(label.name)`、`innerHTML = label.name` のように変更すると危険です。
- ラベル名は今後も `textContent` で扱うべきです。

### 2. ラベル色に長大または不正な CSS / 色文字列を入れる

まずい例:

```xml
<Label id="2" name="Ground" color="rgb(999999999999999999999999999999999999999999999999)" />
```

または:

```xml
<Label id="2" name="Ground" color="url(javascript:alert(1))" />
```

何がまずいか:

- 色文字列をそのまま Three.js や CSS に渡すと、古いライブラリの不具合や過剰な処理を誘発する可能性があります。
- Three.js r124 には `THREE.Color` に極端に長い `rgb(...)` / `hsl(...)` 文字列を渡すとリソース消費が大きくなる DoS 系CVEが報告されています。

現状の対策:

- 現在の実装は `normalizeHexColor(...)` で `#rgb` と `#rrggbb` だけを許可します。
- それ以外は fallback の安全な色に置き換えます。
- そのため、XMLの `color` から長大な `rgb(...)` を `THREE.Color` に渡す経路は抑えられています。

### 3. XMLを極端に大きくする

まずい例:

- 数十MBから数百MB以上の XML
- `Label` 要素が何十万件もある XML
- 極端に深い入れ子を持つ XML

何がまずいか:

- `fetch(...)` 後に `response.text()` と `DOMParser().parseFromString(...)` でXML全体をメモリ上に展開します。
- 巨大XMLはメモリ消費、パース時間増大、ブラウザのフリーズにつながります。

現状の対策:

- 外部URLの `labelMap=` は拒否し、`/data/*.xml` だけを読むようにしています。
- ただし、`/data/` に巨大または不正なXMLを置いた場合、ブラウザ側の負荷問題は起こり得ます。

運用上の注意:

- ラベルXMLは小さな定義ファイルに限定してください。
- 出所不明のXMLを `data/` に置いて読み込まないでください。

### 4. `id` に異常値を入れる

まずい例:

```xml
<Label id="-1" name="Bad" color="#ffffff" />
<Label id="999999999" name="Bad" color="#ffffff" />
<Label id="not-a-number" name="Bad" color="#ffffff" />
```

何がまずいか:

- ラベルIDを配列添字や分類値として無制限に使う実装だと、表示崩れやメモリ消費につながる可能性があります。

現状の対策:

- 現在の実装は `id` を数値化し、整数かつ `0` から `255` の範囲だけを受け付けます。
- 範囲外の `id` は無視されます。

## 悪意ある LAS の具体例

`.las` は点群のバイナリファイルです。XMLのようにHTML文字列を入れてXSSするよりも、主なリスクは「パーサーや描画処理に負荷をかけること」です。

### 1. LASヘッダが壊れている

まずい例:

- 先頭4バイトが `LASF` ではない
- ヘッダサイズが実データと矛盾している
- point record length が `0` または異常値
- point data offset がファイルサイズより大きい

何が起きる可能性があるか:

- 読み込みエラー
- 表示失敗
- 例外発生
- ブラウザの処理停止

現状の対策:

- `LASF` シグネチャを確認しています。
- point record length が `0` の場合はエラーにしています。
- 対応外の point format はエラーにしています。

### 2. 点数やレコード長を異常に大きく見せる

まずい例:

- ヘッダ上の点数が極端に大きい
- 実データとヘッダの点数が一致しない
- record length が不自然に大きい

何が起きる可能性があるか:

- ブラウザのメモリ消費増大
- 読み込み時間増大
- ページのフリーズ
- 描画が極端に重くなる

現状の対策:

- `maxPoints`、`maxReadPoints`、`chunkPoints`、`pointSize` は上限付きでクランプしています。
- `chunkPoints` は typed array の確保量に直結するため、無制限にはしていません。

注意:

- それでも、非常に巨大なLASを全点表示しようとするとブラウザ負荷は高くなります。
- 信頼できるファイルでも、サイズが大きい場合は `maxPoints` や `maxReadPoints` を設定して確認するのが安全です。

### 3. 座標値が極端に大きい、または異常

まずい例:

- scale / offset の組み合わせで座標が極端に大きくなる
- 点群の範囲が異常に広い
- NaN や Infinity 相当を誘発するような壊れた数値構造

何が起きる可能性があるか:

- カメラ位置が極端な場所へ移動する
- 点群が見えない
- 描画が崩れる
- Three.js 側の計算負荷や表示不具合につながる

現状の対策:

- LASの座標は整数値、scale、offsetから計算しています。
- bounds を計算して top view に使っています。

注意:

- 座標範囲の上限検証までは厳密に入れていません。
- 出所不明のLASでは、表示位置や描画負荷が異常になる可能性があります。

### 4. 分類値や点フォーマットを細工する

まずい例:

- 対応外の point format を指定する
- classification offset と record length が矛盾している
- classification 値が意図しない分布になっている

何が起きる可能性があるか:

- ラベル分類が意図通りに出ない
- すべて同じ分類になる
- 表示色やラベル数が想定外になる
- 対応外フォーマットでは読み込みエラーになる

現状の対策:

- point format `0` から `10` 以外はエラーにしています。
- classification offset が取れない形式では分類 `0` として扱います。

## XSSの観点で特に避けるべき変更

現状はかなり抑えていますが、今後の改造で次を行うとXSSリスクが上がります。

避けるべき例:

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

なぜまずいか:

- `label.name` や `file.name` に `<img src=x onerror=...>` のような文字列が入っていると、HTMLとして解釈される可能性があります。
- jQuery 3.1.1 は古く、未信頼HTMLを `.html()` / `.append(htmlString)` に渡すとXSS系CVEの条件に近づきます。

安全な例:

```js
name.textContent = label.name;
```

```js
viewer.setDescription(`Rendering ${escapeHTML(file.name)}`);
```

現状の実装方針:

- ラベル名は `textContent` で表示します。
- Potree description に入る文字列は `escapeHTML(...)` を通します。
- ラベル色は `normalizeHexColor(...)` を通します。
- ローカル `.las` は `File.stream()` で読み、サーバへアップロードしません。

## 説明用の短い回答

質問:

> 悪意のあるファイルとはどんなものですか？

回答:

> 例えば、ラベルXMLの `name` に `<script>` や `<img onerror=...>` のようなHTML/JavaScript風の文字列を入れたもの、`color` に極端に長い `rgb(...)` を入れたもの、何十万件ものラベルを入れた巨大XML、または壊れたLASヘッダや異常に大きい点数・座標を持つLASです。

もう少し具体的には、次のようなファイルは避けてください。

- 送信元や作成者が分からない `.xml` / `.las`
- ラベル名に `<script>`、`<img ...>`、`onerror=`、`javascript:`、`iframe` などHTML/JavaScript風の文字列が入った `.xml`
- ラベルの `color` が `#d2b48c` のような色ではなく、長大な `rgb(...)`、`url(...)`、`javascript:` などになっている `.xml`
- ラベル数が異常に多い、またはサイズが不自然に大きい `.xml`
- `LASF` ではない、ヘッダ情報が壊れている、点数やレコード長が実データと合わない `.las`
- ファイルサイズや点数が用途に対して極端に大きく、ブラウザで開くと固まりそうな `.las`

質問:

> それを使うと何が起きますか？

回答:

> 現状の実装では、ラベル名は `textContent`、色は `#rgb` / `#rrggbb` 制限、ローカルLASはブラウザ内読み込みなので、典型的なXSSや外部送信は抑えています。ただし、悪意あるファイルはブラウザのメモリを大量に使わせたり、ページを固めたり、古いライブラリの脆弱性を突く可能性があります。したがって、出所が分かっている信頼できる `.las` / `.xml` だけを使うべきです。

## 運用上のルール

1. 出所不明の `.las` / `.xml` を読み込まない。
2. XMLのラベル名をHTMLとして表示しない。`textContent` を維持する。
3. XMLの色検証 `normalizeHexColor(...)` を外さない。
4. `viewer.setDescription(...)` に未エスケープ文字列を入れない。
5. 巨大なLASは `maxPoints` / `maxReadPoints` を設定して段階的に確認する。
6. `npm start` の `1234` を外部公開しない。
