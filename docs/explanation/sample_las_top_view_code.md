# `examples/sample_las_top_view.html` コード解説

このドキュメントは、`examples/sample_las_top_view.html` がどのコードで `data/sample.las` を読み込み、Potree/Three.js 上に描画しているかを説明します。特に、外部との通信、ローカルサーバー、外部サーバーにアクセスできる設定になり得る箇所を重点的にまとめます。

## 結論

- このサンプルページ自体には、外部にサーバーを立てる設定はありません。
- 開発用サーバーは `npm start` から `gulp watch` が起動し、`gulpfile.js` の `webserver` タスクで `port: 1234` / `https: false` として起動します。
- `sample_las_top_view.html` の通信は、主に `fetch()` の2箇所です。
  - ラベル定義 XML: `loadLabelDefinitions(labelMapPath)`
  - LAS ファイル本体: `loadLasPoints(samplePath, ...)`
- `file` と `labelMap` はURLクエリで指定できるため、絶対URLを渡すと外部サーバーへアクセスできます。
- ただし、別オリジンの外部URLを読む場合は、相手サーバー側が CORS を許可している必要があります。

## 関連ファイル

- 対象HTML: `examples/sample_las_top_view.html`
- 開発サーバー設定: `gulpfile.js`
- npm起動スクリプト: `package.json`
- 実行手順: `docs/sample-las-setup-ja.md`

## 起動とサーバー設定

`package.json` では、開発起動コマンドが次のように定義されています。

```json
"scripts": {
  "start": "gulp watch",
  "build": "gulp build pack",
  "postinstall": "npm run build"
}
```

つまり、通常は以下で起動します。

```bash
npm start
```

`gulp watch` は `gulpfile.js` の `watch` タスクを実行し、その中で `webserver` タスクも起動します。`webserver` の実体は次の設定です。

```js
connect.server({
  port: 1234,
  https: false,
});
```

このため、ブラウザからは通常以下でアクセスします。

```text
http://localhost:1234/examples/sample_las_top_view.html
```

この設定で明示されているのは `port: 1234` と `https: false` だけです。`sample_las_top_view.html` 側には、外部公開用のホスト名、ドメイン、認証、プロキシ、クラウド接続などの設定はありません。

## 外部に公開されるか

このリポジトリのコード上で確認できる範囲では、外部公開を明示する設定、例えば次のような設定は見当たりません。

- `0.0.0.0`
- `--host 0.0.0.0`
- `public`
- `proxy`
- 外部公開用URL
- 認証付きAPIサーバー設定

ただし、`gulp-connect` の実際の待受アドレスはライブラリの既定挙動にも依存します。外部端末からアクセス可能かどうかは、OS/コンテナ/ファイアウォール/ポート転送の設定にも左右されます。

安全にローカル専用として扱いたい場合は、`localhost` または `127.0.0.1` からだけアクセスする運用にしてください。外部公開したい場合は、別途リバースプロキシ、ファイアウォール、CORS、TLS、認証などを設計する必要があります。

## URLクエリで変わる読み込み対象

`sample_las_top_view.html` の先頭付近で、ブラウザのURLクエリを読み取っています。

```js
const params = new URLSearchParams(window.location.search);
const samplePath = params.get("file") || "../data/sample.las";
const labelMapPath = params.get("labelMap") || "../data/sample_labels.xml";
const maxPointsParam = Number(params.get("maxPoints") || "0");
const maxReadPointsParam = Number(params.get("maxReadPoints") || "0");
const pointSize = Number(params.get("pointSize") || "0.015");
const chunkPoints = Math.max(50000, Number(params.get("chunkPoints") || "1000000"));
```

既定では、同じ開発サーバー配下のローカルファイルをHTTP経由で読みます。

- LAS: `../data/sample.las`
- ラベル定義: `../data/sample_labels.xml`

例えば、以下のURLで点数上限や点サイズを変更できます。

```text
http://localhost:1234/examples/sample_las_top_view.html?maxPoints=3000000&maxReadPoints=3000000&chunkPoints=500000&pointSize=0.015
```

重要なのは、`file` と `labelMap` にURLを指定できる点です。

```text
http://localhost:1234/examples/sample_las_top_view.html?file=https://example.com/data/sample.las&labelMap=https://example.com/data/sample_labels.xml
```

このように指定すると、ブラウザは `example.com` に対して直接 `fetch()` を実行します。つまり、この2つのパラメータは外部通信の入口になり得ます。

## ラベル定義XMLの通信

ラベル定義は `loadLabelDefinitions(url)` で読み込みます。

```js
async function loadLabelDefinitions(url){
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch label map: ${response.status} ${response.statusText}`);
  }

  const xmlText = await response.text();
  const xml = new DOMParser().parseFromString(xmlText, "application/xml");
}
```

この `url` には、先ほどの `labelMapPath` が渡されます。

```js
const labelMapResult = await loadLabelDefinitions(labelMapPath);
```

既定値は `../data/sample_labels.xml` なので、通常は `http://localhost:1234/data/sample_labels.xml` 相当のローカル開発サーバー上のファイルを読みます。

外部URLを指定した場合は、ブラウザがその外部URLへHTTP/HTTPSリクエストを送ります。XMLの取得に失敗した場合でもページ全体を即停止せず、ラベル定義はフォールバックされます。

## LASファイル本体の通信

LASファイルは `loadLasPoints(url, options)` で読み込みます。

```js
async function loadLasPoints(url, options){
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("Streaming fetch is not available in this browser.");
  }

  const totalBytes = Number(response.headers.get("content-length") || "0");
  const reader = response.body.getReader();
}
```

この `url` には、`samplePath` が渡されます。

```js
const result = await loadLasPoints(samplePath, {
  pointLimit,
  readLimit,
  pointSize,
  chunkPoints,
  labelDefinitions: labelMapResult.definitions
});
```

既定値は `../data/sample.las` です。つまり通常は、ローカル開発サーバーから `data/sample.las` を取得します。

この関数は `response.body.getReader()` を使い、LASファイルをストリーミングで読みます。ファイル全体を一度に `arrayBuffer()` にするのではなく、届いたバイト列を順次処理します。

## CORSに関する注意

`file` または `labelMap` に外部URLを指定した場合、ブラウザのCORS制約を受けます。

例:

```text
http://localhost:1234/examples/sample_las_top_view.html?file=https://example.com/sample.las
```

この場合、`https://example.com/sample.las` を配信するサーバー側が、少なくともブラウザからのクロスオリジン取得を許可している必要があります。許可されていない場合、HTTPステータス上は存在するファイルでも、ブラウザ側で `fetch()` がブロックされます。

このサンプルHTML側には、CORSを回避するプロキシ設定や認証ヘッダー設定はありません。CORSを解決する場所は、外部ファイルを配信するサーバー側、または別途用意するプロキシサーバー側です。

## 認証情報やヘッダーの送信

`sample_las_top_view.html` の `fetch()` は、どちらも単純な形式です。

```js
fetch(url)
```

以下のような設定はありません。

- `credentials: "include"`
- `Authorization` ヘッダー
- Cookie送信を意図した設定
- APIキー
- WebSocket
- EventSource
- XMLHttpRequest

そのため、このサンプルが独自に認証情報を外部へ送る構成にはなっていません。ただし、ブラウザの通常仕様として、同一オリジンへのリクエストでは既存Cookieが関係する可能性はあります。このリポジトリのサンプルコード自身にはCookieや認証を扱う処理はありません。

## Potree標準の点群読み込みとの違い

他のPotreeサンプルでは、よく次のようなコードが使われています。

```js
Potree.loadPointCloud("../pointclouds/vol_total/cloud.js", "sigeom.sa", function(e){
  viewer.scene.addPointCloud(e.pointcloud);
});
```

一方、`sample_las_top_view.html` では `Potree.loadPointCloud()` を使っていません。代わりに、LASファイルをブラウザ側で直接 `fetch()` し、ヘッダーや点レコードを手動で解析して、Three.js の `THREE.Points` と `THREE.BufferGeometry` を作っています。

このため、このサンプルの通信先を判断するときは、Potreeの点群メタデータ読み込みではなく、`file` と `labelMap` の2つを見るのが重要です。

## LAS解析の流れ

`loadLasPoints()` は、受信したバイト列からまずLASヘッダーを解析します。

```js
const signature = String.fromCharCode(buffer[0], buffer[1], buffer[2], buffer[3]);
if (signature !== "LASF") {
  throw new Error("Invalid LAS signature. Expected LASF.");
}
```

ヘッダーから以下を読み取ります。

- LASバージョン
- ヘッダーサイズ
- 点データ開始位置
- 点フォーマット
- 点レコード長
- 点数
- 座標スケール
- 座標オフセット

その後、点レコードごとに `x/y/z` の整数値を読み、LASヘッダーのスケールとオフセットを使って実座標へ変換します。

```js
const x = xi * header.scaleX + header.offsetX;
const y = yi * header.scaleY + header.offsetY;
const z = zi * header.scaleZ + header.offsetZ;
```

classification は点フォーマットによってバイト位置が変わるため、`getClassificationOffset()` で取得しています。

```js
function getClassificationOffset(pointFormat){
  if (pointFormat >= 0 && pointFormat <= 5) {
    return 15;
  }
  if (pointFormat >= 6 && pointFormat <= 10) {
    return 16;
  }
  return -1;
}
```

## 描画データの作り方

読み込んだ点は、classification ごとにグループ化されます。

- `createLabelPointCollector()`
- `createLabelChunkCollector()`

各ラベルごとに `THREE.Group` を作り、その中へチャンク単位の `THREE.Points` を追加します。チャンク単位にしているのは、巨大なLASを1つの巨大なGeometryにまとめるより、メモリと描画管理を扱いやすくするためです。

```js
const geometry = new THREE.BufferGeometry();
geometry.setAttribute(
  "position",
  new THREE.BufferAttribute(positions.subarray(0, writtenInChunk * 3), 3)
);

const points = new THREE.Points(geometry, material);
pointsGroup.add(points);
```

ラベルごとに `THREE.PointsMaterial` を持つため、ラベルの色変更や表示/非表示切り替えができます。

## UIの動作

右上のLabelsパネルは `renderLabelLegend(labelEntries)` で作成されます。

- チェックボックス: ラベルごとの表示/非表示
- 色ボタン: ラベル色の変更
- 点数表示: ラベルごとの描画点数

チェックボックス変更時は、対応する `THREE.Group` の `visible` を切り替えます。

```js
toggle.addEventListener("change", () => {
  label.setVisible(toggle.checked);
});
```

色変更時は、対応する `THREE.PointsMaterial` の色を変更します。

```js
label.setColor(next);
```

## トップビューと平面

読み込み完了後、点群のバウンディングボックスから表示範囲を計算し、上から見るカメラ位置に移動します。

```js
applyTopView(viewer, result.bounds);
```

また、点群の下に半透明の平面を追加します。

```js
const basePlane = createPlane(result.bounds);
viewer.scene.scene.add(basePlane);
```

この平面は外部通信とは無関係で、Three.js の `PlaneGeometry` と `MeshBasicMaterial` でページ内生成されています。

## このサンプルで外部通信になり得る場所の一覧

| 場所 | 既定値 | 外部通信になり得る条件 |
| --- | --- | --- |
| `labelMap` クエリ | `../data/sample_labels.xml` | `?labelMap=https://...` を指定した場合 |
| `file` クエリ | `../data/sample.las` | `?file=https://...` を指定した場合 |
| CSS/JSライブラリ読み込み | `../libs/...`, `../build/...` | HTMLを書き換えて外部CDN等にした場合 |
| 開発サーバー | `localhost:1234` で利用 | OS/ネットワーク側でポートを外部公開した場合 |

## 外部サーバーにアクセスさせたくない場合の確認ポイント

1. ブラウザのアドレスバーで `file=` と `labelMap=` に `http://` または `https://` の絶対URLが入っていないことを確認する。
2. `examples/sample_las_top_view.html` の既定値が `../data/sample.las` と `../data/sample_labels.xml` のままであることを確認する。
3. 開発サーバーを外部公開するためのポートフォワード、コンテナポート公開、リバースプロキシ設定をしていないことを確認する。
4. ブラウザのDevToolsのNetworkタブで、アクセス先が `localhost:1234` または同一ホストだけになっていることを確認する。

## 外部サーバーのファイルを読みたい場合

外部サーバー上のLAS/XMLを読みたい場合は、次のようなURLを使います。

```text
http://localhost:1234/examples/sample_las_top_view.html?file=https://example.com/points/sample.las&labelMap=https://example.com/points/sample_labels.xml
```

外部サーバー側では、少なくとも次を満たす必要があります。

- LAS/XMLを静的ファイルとして配信できること
- ブラウザからのCORSを許可していること
- 大きなLASを配信できるタイムアウト/サイズ制限になっていること
- 可能なら `Content-Length` を返すこと

`Content-Length` がない場合でも読み込み自体は進みますが、ステータス表示のパーセント表示はできません。

## まとめ

`examples/sample_las_top_view.html` は、ローカル開発サーバー上のHTMLとして動き、LAS/XMLをブラウザ側の `fetch()` で読むサンプルです。外部公開用のサーバー設定はHTML内にはありません。外部通信として注意すべき箇所は、URLクエリの `file` と `labelMap` です。これらに外部URLを渡すと、ブラウザがその外部サーバーへ直接アクセスします。
