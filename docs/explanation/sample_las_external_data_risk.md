# `sample_las_top_view.html` の外部送信・外部アクセスリスク

このドキュメントは、`examples/sample_las_top_view.html` を `npm start` 後に実行するうえで、点群データが外部へ送信される危険性、または外部 PC から点群データへアクセスできる可能性がある箇所をコードから確認した結果です。

## 結論

`examples/sample_las_top_view.html` には、読み込んだ LAS 点群データを外部サーバーへアップロードする処理は見当たりません。

確認した限り、この HTML でネットワーク通信を明示的に行う箇所は、次の2つの `fetch()` です。

- ラベル定義 XML の取得: `loadLabelDefinitions(labelMapPath)`
- LAS ファイル本体の取得: `loadLasPoints(samplePath, ...)`

つまり、このサンプルの通信は基本的に「外部へ送る」ではなく「ブラウザが指定 URL から読む」です。ただし、次の条件では外部アクセスリスクがあります。

- 開発サーバー `localhost:1234` を Docker / VM / WSL / Codespaces / SSH / firewall 設定などで外部公開した場合
- URL クエリ `file=` または `labelMap=` に外部 URL を指定した場合
- 外部公開した状態で `data/sample.las` など機密の点群ファイルを repo 配下に置いた場合

## 対象ファイル

- HTML: `examples/sample_las_top_view.html`
- 開発サーバー設定: `gulpfile.js`
- npm script: `package.json`
- `gulp-connect` 実装確認: `node_modules/gulp-connect/index.js`

## `sample_las_top_view.html` の通信入口

HTML 内では URL クエリから読み込み先を決めています。

```js
const params = new URLSearchParams(window.location.search);
const samplePath = params.get("file") || "../data/sample.las";
const labelMapPath = params.get("labelMap") || "../data/sample_labels.xml";
```

既定値:

- `samplePath`: `../data/sample.las`
- `labelMapPath`: `../data/sample_labels.xml`

通信上の意味:

- 通常は同じ開発サーバー上の `data/sample.las` と `data/sample_labels.xml` を読みます。
- `?file=https://example.com/a.las` のように指定すると、ブラウザが `https://example.com/a.las` へ直接 `fetch()` します。
- `?labelMap=https://example.com/labels.xml` も同様に外部 URL へアクセスします。

## ラベル定義 XML の取得

関数:

- `loadLabelDefinitions(url)`

該当コード:

```js
const response = await fetch(url);
const xmlText = await response.text();
```

呼び出し:

```js
const labelMapResult = await loadLabelDefinitions(labelMapPath);
```

リスク:

- `labelMapPath` が既定値なら `http://localhost:1234/data/sample_labels.xml` 相当を読みます。
- `labelMap=` に外部 URL を指定すると、その外部サーバーへブラウザから GET リクエストが送られます。
- ここで点群本体は送信されません。ただし、外部サーバー側にはアクセス元 IP、Referer、User-Agent など通常の HTTP リクエスト情報が残る可能性があります。

## LAS ファイル本体の取得

関数:

- `loadLasPoints(url, options)`

該当コード:

```js
const response = await fetch(url);
const reader = response.body.getReader();
```

呼び出し:

```js
const result = await loadLasPoints(samplePath, {
  pointLimit,
  readLimit,
  pointSize,
  chunkPoints,
  labelDefinitions: labelMapResult.definitions
});
```

リスク:

- `samplePath` が既定値なら `http://localhost:1234/data/sample.las` 相当を読みます。
- `file=` に外部 URL を指定すると、ブラウザがその外部 URL へ LAS ファイルを取りに行きます。
- この処理は LAS ファイルを外部へ送信するものではなく、外部またはローカルサーバーから取得する処理です。
- 開発サーバーが外部公開されている場合、別 PC からも `http://<公開ホスト>:1234/data/sample.las` を直接 GET できる可能性があります。

## 外部へデータを送信する処理の有無

次のような明示的な外部送信処理は、`examples/sample_las_top_view.html` 内には見当たりません。

- `fetch(url, { method: "POST" })`
- `fetch(url, { method: "PUT" })`
- `XMLHttpRequest`
- `navigator.sendBeacon`
- `WebSocket`
- `EventSource`
- `document.cookie` を読む処理
- `Authorization` ヘッダーを付ける処理
- `credentials: "include"` を付ける処理

この HTML の `fetch()` は単純な GET です。

```js
fetch(url)
```

そのため、HTML の実装だけを見る限り、点群データを外部へアップロードする設計にはなっていません。

## 外部 PC からデータにアクセスできる条件

`npm start` は `package.json` の次の script です。

```json
"start": "gulp watch"
```

`gulpfile.js` の開発サーバー設定は次の通りです。

```js
connect.server({
  port: 1234,
  https: false,
});
```

この repo の `node_modules/gulp-connect/index.js` では、`host` 未指定時の既定値が `localhost` です。

```js
this.host = options.host || "localhost";
```

さらに起動時は次の形で listen します。

```js
this.server.listen(this.port, this.host, ...)
```

したがって、通常の `npm start` だけであれば、外部 PC から直接見える可能性は低いです。

ただし、次のいずれかを行うと外部 PC から見える可能性があります。

| 条件 | 例 | 何が見える可能性があるか |
|---|---|---|
| サーバーを全インターフェース待受にする | `host: "0.0.0.0"` | HTML、JS、`data/sample.las` |
| Docker で port publish する | `docker run -p 1234:1234 ...` | ホスト経由で `1234` 配下 |
| VM で port forwarding する | Host `1234` -> Guest `1234` | VM 内の開発サーバー |
| WSL portproxy を使う | `listenaddress=0.0.0.0 listenport=1234` | Windows 経由で WSL 側サーバー |
| Codespaces の port を Public にする | Forwarded Ports の Visibility を Public | 公開 URL 配下 |
| SSH reverse forwarding を使う | `ssh -R 0.0.0.0:1234:localhost:1234 ...` | リモートホスト経由 |
| firewall で `1234` を許可する | LAN / WAN から到達可能 | 公開ホスト上のファイル |

外部公開された場合、認証はないため、URL を知っている外部 PC は次のような URL に直接アクセスできる可能性があります。

```text
http://<公開ホスト>:1234/examples/sample_las_top_view.html
http://<公開ホスト>:1234/data/sample.las
http://<公開ホスト>:1234/data/sample_labels.xml
```

## `file=` / `labelMap=` による外部通信

次のように URL を開いた場合:

```text
http://localhost:1234/examples/sample_las_top_view.html?file=https://example.com/points/sample.las&labelMap=https://example.com/points/sample_labels.xml
```

ブラウザは次の通信を行います。

- `localhost:1234` から HTML / JS / CSS を取得する。
- `https://example.com/points/sample.las` から LAS を取得する。
- `https://example.com/points/sample_labels.xml` から XML を取得する。

この場合、点群データが `localhost` から外部へアップロードされるわけではありません。しかし、外部サーバーへアクセスするため、外部サーバーにはアクセスログが残る可能性があります。また、外部 URL の CORS 設定によってはブラウザが取得をブロックします。

## script / CSS / 画像の読み込み

`examples/sample_las_top_view.html` の `<script src=...>` や `<link rel=...>` は、確認した範囲では相対パスです。

例:

- `../libs/jquery/jquery-3.1.1.min.js`
- `../libs/openlayers3/ol.css`
- `../build/potree/potree.js`
- `../libs/plasio/js/laslaz.js`
- `../build/potree/resources/images/background.jpg`

これらは通常、同じ `localhost:1234` の開発サーバーから取得されます。CDN のような外部 URL へ script を取りに行く記述は、この HTML 内には見当たりません。

## ブラウザ内処理と外部通信の区別

このサンプルでは、LAS を取得した後、ブラウザ内で次の処理を行います。

- LAS ヘッダー解析
- 点レコードの読み取り
- label / classification によるグループ化
- `THREE.BufferGeometry` / `THREE.Points` の生成
- 画面描画

これらはブラウザ内のメモリと GPU で行われる処理です。処理済み点群をサーバーへ返すコードはありません。

## 安全に実行するための確認項目

ローカルだけで安全に確認する場合:

1. URL は `http://localhost:1234/examples/sample_las_top_view.html` を使う。
2. `gulpfile.js` に `host: "0.0.0.0"` を追加しない。
3. Docker / VM / WSL / Codespaces / SSH で port `1234` を外部公開しない。
4. firewall で port `1234` を外部から許可しない。
5. `file=` と `labelMap=` に外部 URL を指定しない。
6. DevTools の Network タブで、`sample.las` と `sample_labels.xml` の取得先が意図したホストだけであることを確認する。

外部公開が必要な場合:

- 開発サーバーをそのまま公開しない。
- 認証を入れる。
- TLS を使う。
- IP 制限または VPN 内限定にする。
- 配信するディレクトリを必要最小限にする。
- 機密の LAS / LAZ / 点群ファイルを repo の公開配信範囲に置かない。

## 判定まとめ

| 観点 | 判定 | 根拠 |
|---|---|---|
| 点群データを外部へアップロードする処理 | 見当たらない | POST / PUT / sendBeacon / WebSocket なし |
| 点群データを取得する処理 | あり | `loadLasPoints()` の `fetch(samplePath)` |
| 外部 URL へアクセスする入口 | あり | URL クエリ `file=` / `labelMap=` |
| 外部 PC から `sample.las` を直接読む可能性 | 条件付きであり | port `1234` を外部公開した場合 |
| 認証付き配信 | なし | `gulp-connect` の静的開発サーバー |
| 通常の `npm start` だけで外部公開 | 低い | `gulp-connect` の既定 host は `localhost` |
