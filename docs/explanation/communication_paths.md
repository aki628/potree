# Potree の通信箇所まとめ

このドキュメントは、`npm start` 後に `examples/sample_las_top_view.html` を操作する場合に、どこで通信が発生するか、外部 PC から点群データを見られる条件がどこにあるかをまとめます。

## 結論

`examples/sample_las_top_view.html` 自体の通信は主に2箇所です。

- `loadLabelDefinitions(labelMapPath)` の `fetch(url)`
  - 既定: `../data/sample_labels.xml`
  - URLクエリ `labelMap=...` で変更可能
- `loadLasPoints(samplePath, ...)` の `fetch(url)`
  - 既定: `../data/sample.las`
  - URLクエリ `file=...` で変更可能

`npm start` で起動する開発サーバーは `gulpfile.js` の `connect.server({ port: 1234, https: false })` です。この repo の `gulp-connect` は `host` 未指定時に `localhost` を使うため、通常は自分の PC から `http://localhost:1234/...` で見る用途です。

ただし、Docker / VM / WSL / Codespaces / SSH port forwarding / firewall 設定などで `1234` を外部へ公開すると、外部 PC からも `data/sample.las` や HTML / JS / build 成果物を読める可能性があります。この開発サーバーには認証機構がありません。

## 開発サーバー

対象ファイル:

- `package.json`
- `gulpfile.js`

`package.json` では、`npm start` が `gulp watch` を起動します。

```json
"scripts": {
  "start": "gulp watch"
}
```

`gulpfile.js` の `webserver` は次の設定です。

```js
connect.server({
  port: 1234,
  https: false,
});
```

通信上の意味:

- HTTP サーバーが port `1234` で起動する。
- HTTPS ではないため、通信は平文 HTTP。
- repo 内の HTML、JS、CSS、`data/` 配下のファイルなどがブラウザから取得可能になる。
- `host` は明示されていない。この環境の `node_modules/gulp-connect/index.js` では既定値が `localhost`。
- `localhost` のままなら通常は同じ PC 内からしか見えない。
- 外部公開設定を追加すると、認証なしで外部 PC から見える可能性がある。

## sample_las_top_view.html の通信

対象ファイル:

- `examples/sample_las_top_view.html`

### URLクエリの読み取り

ページ先頭の module script で URL クエリを読みます。

```js
const params = new URLSearchParams(window.location.search);
const samplePath = params.get("file") || "../data/sample.las";
const labelMapPath = params.get("labelMap") || "../data/sample_labels.xml";
```

通信上の意味:

- `file` 未指定なら `../data/sample.las` を読む。
- `labelMap` 未指定なら `../data/sample_labels.xml` を読む。
- `file=https://example.com/sample.las` のように絶対 URL を渡すと、ブラウザがその外部 URL へ直接アクセスする。
- 外部 URL への取得はブラウザの CORS 制約を受ける。

### ラベル定義 XML の取得

関数:

- `loadLabelDefinitions(url)`

通信コード:

```js
const response = await fetch(url);
const xmlText = await response.text();
```

既定の通信先:

```text
http://localhost:1234/data/sample_labels.xml
```

外部公開時のリスク:

- 開発サーバーが外部から見える場合、外部 PC は同じ XML を取得できる。
- `labelMap` に外部 URL を指定した場合、閲覧しているブラウザが外部サーバーへアクセスする。

### LAS ファイル本体の取得

関数:

- `loadLasPoints(url, options)`

通信コード:

```js
const response = await fetch(url);
const reader = response.body.getReader();
```

既定の通信先:

```text
http://localhost:1234/data/sample.las
```

特徴:

- `fetch()` で LAS ファイルを取得する。
- `response.body.getReader()` を使い、レスポンス body を streaming reader として読む。
- `Authorization` ヘッダー、Cookie 送信指定、API key、WebSocket、EventSource は使っていない。

外部公開時のリスク:

- 開発サーバーが外部から見える場合、外部 PC は `http://<公開ホスト>:1234/data/sample.las` を直接取得できる可能性がある。
- `sample_las_top_view.html` は LAS をブラウザ側で解析するため、サーバー側にデータ保護や点群単位の権限制御はない。

## 外部 PC から見える条件

外部 PC から点群データが見えるかどうかは、次の条件で決まります。

| 条件 | 通常状態 | リスクが上がる状態 |
|---|---|---|
| サーバーの待受 | `localhost` | `0.0.0.0` や LAN IP |
| ポート公開 | 外部公開なし | Docker `-p 1234:1234`、VM port forwarding、WSL portproxy、Codespaces Public port、SSH reverse tunnel |
| ファイアウォール | 外部から遮断 | `1234` が許可されている |
| URL指定 | `../data/sample.las` | `file=` に外部 URL |
| 認証 | なし | なしのまま外部公開すると危険 |

### Docker の例

次のように port publish すると、ホスト側の port `1234` に公開されます。

```bash
docker run -p 1234:1234 your-image
```

`docker-compose.yml` では次の設定が該当します。

```yaml
ports:
  - "1234:1234"
```

アプリ側が `localhost` にしか bind していなければコンテナ外から届かない場合もありますが、`host: "0.0.0.0"` などに変えると外部から到達しやすくなります。

### VM の例

VirtualBox などで NAT port forwarding を設定すると、ホストの port `1234` が VM 内の port `1234` に転送されます。

```text
Host port: 1234
Guest port: 1234
```

この状態でホスト側の firewall が許可していると、LAN から `http://<ホストIP>:1234/...` で見える可能性があります。

### WSL の例

Windows 側で `netsh interface portproxy` を使うと、Windows の待受 port から WSL へ転送できます。

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=1234 connectaddress=<WSLのIP> connectport=1234
```

確認:

```powershell
netsh interface portproxy show all
```

`listenaddress=0.0.0.0` は全インターフェース待受のため、firewall 設定次第で外部 PC から見える可能性があります。

### Codespaces / cloud IDE の例

GitHub Codespaces などでは、起動中の port が Forwarded Ports に表示されます。

- `Private`: 基本的に自分だけがアクセスできる。
- `Public`: URL を知っている外部ユーザーがアクセスできる可能性がある。

`1234` を Public にした場合、`https://...app.github.dev` のような URL 経由で `examples/sample_las_top_view.html` や `data/sample.las` が見える可能性があります。

### SSH port forwarding の例

ローカルからリモートの `localhost:1234` を見るだけの転送:

```bash
ssh -L 1234:localhost:1234 user@remote-host
```

通常これは自分のローカル PC 側だけで使う形です。

一方、reverse forwarding でリモート側に公開すると外部公開になり得ます。

```bash
ssh -R 0.0.0.0:1234:localhost:1234 user@remote-host
```

SSH サーバー側の `GatewayPorts` 設定によっては、リモートホストの外部インターフェースで待ち受けます。

## Potree 標準 loader の通信箇所

`sample_las_top_view.html` とは別に、Potree 本体にも点群・補助データを読む通信箇所があります。

| ファイル | 通信方法 | 読むもの |
|---|---|---|
| `src/loader/POCLoader.js` | XHR | `cloud.js` など Potree 1.x メタデータ |
| `src/loader/BinaryLoader.js` | XHR | Potree binary node |
| `src/loader/LasLazLoader.js` | XHR | LAS / LAZ データ |
| `src/PointCloudOctreeGeometry.js` | XHR | `.hrc` hierarchy |
| `src/loader/EptLoader.js` | `fetch()` | `ept.json` |
| `src/PointCloudEptGeometry.js` | `fetch()` | `ept-hierarchy/*.json` |
| `src/loader/ept/LaszipLoader.js` | `fetch()` | `ept-data/*.laz` |
| `src/loader/ept/BinaryLoader.js` | XHR | EPT `.bin` |
| `src/loader/ept/ZstandardLoader.js` | XHR | EPT `.zst` |
| `src/modules/loader/2.0/OctreeLoader.js` | `fetch()` + `Range` header | `metadata.json`、`octree.bin`、`hierarchy.bin` |
| `src/loader/GeoPackageLoader.js` | `fetch()` + `Utils.loadScript()` | `.gpkg`、`geopackage.js`、`sql-wasm.js`、`sql-wasm.wasm` |
| `src/modules/Images360/Images360.js` | `fetch()` / texture load | `coordinates.txt`、画像 |
| `src/modules/OrientedImages/OrientedImages.js` | `fetch()` / texture load | camera/image params、画像 |

これらは、`Potree.loadPointCloud(...)` など標準の Potree 読み込み経路を使った場合に関係します。`examples/sample_las_top_view.html` は標準の `Potree.loadPointCloud()` ではなく、自前の `fetch()` で `sample.las` を読むため、まず見るべき箇所は `samplePath` と `labelMapPath` です。

## Worker の postMessage は外部通信ではない

対象ファイル:

- `src/WorkerPool.js`
- `src/workers/*.js`
- `src/modules/loader/2.0/DecoderWorker*.js`

例:

```js
let worker = new Worker(url);
worker.postMessage(message, [message.buffer]);
```

worker 側:

```js
postMessage(message, transferables);
```

これはブラウザ内のメインスレッドと Web Worker の通信です。外部サーバーへ送信しているわけではありません。ただし、worker スクリプト自体は `build/potree/workers/*.js` として HTTP サーバーからブラウザへ配信されます。

## 安全確認手順

ローカル専用で作業したい場合は次を確認します。

1. 開く URL を `http://localhost:1234/examples/sample_las_top_view.html` にする。
2. `gulpfile.js` に `host: "0.0.0.0"` を追加しない。
3. Docker / VM / WSL / Codespaces / SSH で port `1234` を公開しない。
4. firewall で port `1234` を外部から許可しない。
5. ブラウザ DevTools の Network タブで、`data/sample.las` と `data/sample_labels.xml` が意図したホストからだけ取得されていることを確認する。
6. `file=` や `labelMap=` に外部 URL を指定しない。

外部公開する必要がある場合は、開発サーバーをそのまま公開せず、認証、TLS、アクセス元制限、データ配置範囲の制限、ログ確認を入れた別の配信方法を用意してください。
