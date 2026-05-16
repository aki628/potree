# `examples/sample_las_top_view.html` の外部送信・外部アクセスリスク調査

対象は `examples/sample_las_top_view.html` 本体と、この HTML が操作中に読み込むライブラリです。

## 結論

通常の `npm start` のまま `http://localhost:1234/examples/sample_las_top_view.html` を自分のPC上のブラウザで開く範囲では、点群データを外部サーバへアップロードする処理は見つかりませんでした。

ただし、次の2点は注意が必要です。

1. `file=` または `labelMap=` クエリに外部URLを指定すると、ブラウザはその外部URLへ LAS または XML を取りに行きます。
2. GUI 初期化で Potree の地図機能が作られ、OpenLayers の OSM タイルソースが使われます。これにより OpenStreetMap タイルサーバへ画像タイル取得の GET が出る可能性があります。点群ファイル本体を送る処理ではありませんが、利用者のIPアドレス、User-Agent、地図タイル座標、ズーム値は外部に見えます。

外部から点群データへアクセスされるかどうかは、ほぼ開発サーバの公開状態で決まります。通常の `gulp-connect` は `localhost` に bind しますが、`0.0.0.0` bind、Docker/VM/WSL/Codespaces/SSH の port forward、リバースプロキシなどで `1234` を外部公開すると、公開先から `examples/` や `data/` 以下を HTTP GET できる可能性があります。

## HTML が直接読み込むライブラリ

`examples/sample_las_top_view.html` は次を読み込みます。

- `libs/jquery/jquery-3.1.1.min.js`
- `libs/spectrum/spectrum.js`
- `libs/jquery-ui/jquery-ui.min.js`
- `libs/other/BinaryHeap.js`
- `libs/tween/tween.min.js`
- `libs/d3/d3.js`
- `libs/proj4/proj4.js`
- `libs/openlayers3/ol.js`
- `libs/i18next/i18next.js`
- `libs/jstree/jstree.js`
- `build/potree/potree.js`
- `libs/plasio/js/laslaz.js`
- `libs/three.js/build/three.module.js`

この中で、サンプル操作時の外部通信リスクとして見るべきものは主に `build/potree/potree.js`、`libs/openlayers3/ol.js`、`libs/i18next/i18next.js`、`libs/jstree/jstree.js`、Three.js の WebXR 関連です。

## サンプル本体の通信

### LAS ファイル取得

`samplePath` は URL クエリの `file`、未指定なら `../data/sample.las` です。

```js
const params = new URLSearchParams(window.location.search);
const samplePath = params.get("file") || "../data/sample.las";
```

実際の読み込みは `fetch(url)` です。

```js
async function loadLasPoints(url, options){
  const response = await fetch(url);
  const reader = response.body.getReader();
}
```

通常は同じ開発サーバ上の `data/sample.las` を GET します。外部へ送信するのではなく、ブラウザがデータを取得します。

ただし、次のように外部URLを指定すると、その外部サーバへ GET が出ます。

```text
http://localhost:1234/examples/sample_las_top_view.html?file=https://example.com/sample.las
```

この場合でも、送られるのは点群ファイルそのものではなく、ブラウザから外部URLへの取得リクエストです。外部サーバ側にはアクセス元IP、User-Agent、Referer などが見える可能性があります。

### ラベルXML取得

`labelMapPath` は URL クエリの `labelMap`、未指定なら `../data/sample_labels.xml` です。

```js
const labelMapPath = params.get("labelMap") || "../data/sample_labels.xml";
```

実際の読み込みは `fetch(url)` です。

```js
async function loadLabelDefinitions(url){
  const response = await fetch(url);
  const xmlText = await response.text();
}
```

これも通常はローカル開発サーバ上の XML を GET します。`labelMap=https://...` を指定した場合だけ外部URLへ GET します。

## Potree GUI 初期化で発生する通信

`sample_las_top_view.html` は `viewer.loadGUI(...)` を呼びます。この中で複数の追加リソースが読み込まれます。

### ローカルHTMLの読み込み

`src/viewer/viewer.js` では jQuery の `.load()` で Potree の GUI HTML を読み込みます。

```js
sidebarContainer.load(new URL(Potree.scriptPath + '/sidebar.html').href, () => {
```

さらに profile UI もローカルから読み込みます。

```js
let elProfile = $('<div>').load(new URL(Potree.scriptPath + '/profile.html').href, () => {
```

これらは通常 `build/potree/sidebar.html` と `build/potree/profile.html` への同一オリジン GET です。外部送信ではありません。

### i18next の言語ファイル読み込み

GUI 初期化で i18next が初期化されます。

```js
i18n.init({
  lng: 'en',
  resGetPath: Potree.resourcePath + '/lang/__lng__/__ns__.json',
  preload: ['en', 'fr', 'de', 'jp', 'se', 'es', 'zh', 'it','ca'],
  getAsync: true,
  debug: false
}, function (t) {
  $('body').i18n();
});
```

`libs/i18next/i18next.js` 自体には `XMLHttpRequest`、GET、POST、Cookie、localStorage を使う機能があります。特に `sendMissing` を有効化すると不足翻訳キーを POST できる実装があります。

しかし、このサンプルの初期化では `sendMissing` は指定されていません。したがって通常は `build/potree/resources/lang/...` の JSON をローカル GET する用途です。点群データを送る経路ではありません。

### jstree

`libs/jstree/jstree.js` には AJAX でツリーをロードする機能があります。

ただし Potree の sidebar 初期化では、`core.data.url` や `ajax` を指定していません。

```js
tree.jstree({
  'plugins': ["checkbox", "state"],
  'core': {
    "dblclick_toggle": false,
    "state": {"checked" : true},
    'check_callback': true,
    "expand_selected_onload": true
  }
});
```

そのため、このサンプル操作で jstree が外部へ点群データを送る経路は見つかりませんでした。`localStorage.removeItem('jstree')` はありますが、これはブラウザ内の保存領域操作です。

## OpenLayers / MapView

Potree GUI 初期化では MapView が作られます。

```js
this.mapView = new MapView(this);
this.mapView.init();
```

`src/viewer/map.js` の `MapView.init()` は OpenLayers の地図に OSM タイルソースを追加します。

```js
new ol.layer.Tile({source: new ol.source.OSM()}),
```

`libs/openlayers3/ol.js` の `ol.source.OSM` のデフォルトURLは次です。

```text
https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

したがって、地図ビューが初期化・描画・表示されると OpenStreetMap へタイル画像取得の GET が出る可能性があります。

これは点群データのアップロードではありませんが、外部に次の情報が見える可能性があります。

- 利用者のIPアドレス
- ブラウザの User-Agent
- Referer
- 表示された地図タイルの `z/x/y`

`sample_las_top_view.html` は点群を `THREE.Points` として直接 scene に追加しており、通常の `Potree.loadPointCloud(...)` の点群ロードではありません。そのため `MapView.load(pointcloud)` 内の `sources.json` 取得は、このサンプルの通常経路では発火しないと見てよいです。

```js
let url = `${pointcloud.pcoGeometry.url}/../sources.json`;
fetch(url).then(async (response) => {
```

ただし、別途 Potree 点群を読み込むコードを追加した場合は、点群URL近傍の `sources.json` を同一オリジンまたは指定URLから取得します。

## Three.js / WebXR 関連

GUI 初期化では VR ボタン作成も呼ばれます。

```js
VRButton.createButton(this.renderer).then(vrButton => {
```

`VRButton.createButton(...)` 自体は WebXR サポート確認とセッション開始用のUI作成が中心で、これだけで点群データを外部送信する経路は見つかりません。

ただし Three.js の `XRControllerModelFactory` には、WebXR コントローラープロファイル取得用の外部URLが含まれています。

```js
const DEFAULT_PROFILES_PATH = 'https://cdn.jsdelivr.net/npm/@webxr-input-profiles/assets@1.0/dist/profiles';
```

`src/navigation/VRControls.js` は VR コントローラーモデル用に `XRControllerModelFactory` を作ります。

```js
const controllerModelFactory = new XRControllerModelFactory();
```

そのため、VR に入り、コントローラーモデル読み込みが動く条件では `cdn.jsdelivr.net` へ WebXR 入力プロファイルやアセットを取りに行く可能性があります。これも点群データのアップロードではありませんが、外部CDNへの GET です。

## Profile / Volume のサーバ連携機能

Potree には、計測した Profile や Volume の範囲をサーバへ渡し、抽出結果をダウンロードする機能があります。

`ProfilePanel` には次のようなURL生成があります。

```js
let url = `${viewer.server}/create_regions_filter?pointclouds=[${pointcloudsArg}]&regions=[${regionsArg}]`;
let response = await fetch(url);
```

`VolumePanel` も同様に `viewer.server` を使います。

ただし `viewer.server` の初期値は `null` です。

```js
this.server = null;
```

また、`sample_las_top_view.html` では `viewer.setServer(...)` を呼んでいません。したがって通常のこのサンプル操作では、このサーバ連携機能は無効です。

もし別途 `viewer.setServer("https://example.com")` のような設定を追加した場合、選択範囲、点群パス、変換行列などがそのサーバへ GET クエリとして送られる可能性があります。

## plasio / LAS LAZ 関連

`libs/plasio/js/laslaz.js` は HTML で読み込まれていますが、現在の `sample_las_top_view.html` は独自の LAS パーサーで `fetch` したバイト列を読み、`THREE.Points` を生成しています。

plasio 側には worker や `postMessage` を使う処理がありますが、これはブラウザ内のメインスレッドと worker の通信です。外部HTTP送信ではありません。

## 外部からアクセスされるリスク

外部から `data/sample.las` や `examples/sample_las_top_view.html` を見られるかは、開発サーバがどのアドレスに bind され、どこへ公開されているかで決まります。

`package.json` の `npm start` は `gulp watch` です。`gulpfile.js` のサーバ設定は次です。

```js
connect.server({
  port: 1234,
  https: false,
});
```

`gulp-connect` は `host` 未指定時に `localhost` を使います。

```js
this.host = options.host || "localhost";
```

つまり通常は同じPCからの `localhost:1234` アクセス用です。

危険になるのは次のような場合です。

- `gulpfile.js` に `host: "0.0.0.0"` を追加する
- Docker で `-p 1234:1234` のように公開する
- VM/WSL/Codespaces でポート `1234` をホストやインターネットへ forward する
- SSH port forwarding で第三者が到達できる形にする
- nginx などのリバースプロキシで `localhost:1234` を公開する

この状態では、到達できる相手が次のようなURLを直接 GET できる可能性があります。

```text
http://公開ホスト:1234/examples/sample_las_top_view.html
http://公開ホスト:1234/data/sample.las
http://公開ホスト:1234/data/sample_labels.xml
```

## リスクを下げる設定

外部送信を極力避けたい場合は、次を守るのが有効です。

- `gulpfile.js` に `host: "0.0.0.0"` を追加しない。
- Docker / VM / WSL / Codespaces / SSH で `1234` を外部公開しない。
- `file=` と `labelMap=` に外部URLを指定しない。
- GUI の地図が不要なら `viewer.loadGUI(...)` を使わない、または `MapView` / `ol.source.OSM()` の初期化を無効にする。
- VR が不要なら VR ボタンや `VRControls` を使わない。
- サーバ連携が不要なら `viewer.setServer(...)` を追加しない。

## 判定表

| 経路 | 通常サンプルで発火 | 外部送信の内容 | 点群データ送信リスク |
|---|---:|---|---:|
| `loadLasPoints(fetch(samplePath))` | はい | 通常はローカル `sample.las` の GET | 低。外部URL指定時は外部GET |
| `loadLabelDefinitions(fetch(labelMapPath))` | はい | 通常はローカル XML の GET | 低。外部URL指定時は外部GET |
| `viewer.loadGUI()` の sidebar/profile `.load()` | はい | ローカルHTMLの GET | 低 |
| i18next 言語JSON | はい | ローカル言語JSONの GET | 低 |
| jstree AJAX | いいえ | 設定すれば任意URLへ AJAX | 通常は低 |
| OpenLayers OSM | 条件付きであり得る | OSM タイル画像 GET | 点群本体は送らないが外部アクセスあり |
| WebXR controller profiles | VR利用時にあり得る | jsDelivr への profile/asset GET | 点群本体は送らない |
| Profile/Volume `viewer.server` | いいえ | 設定時に範囲・点群パス等をサーバへ GET | 設定時は注意 |
| 開発サーバ `localhost:1234` | はい | ローカル公開 | 外部公開しなければ低 |
| `0.0.0.0` / port forward | 設定時のみ | 外部から `data/` を GET 可能 | 高くなる |

