# worker / lazy lib / shader ソースコード解説

このドキュメントは、`gulpfile.js` の `workers` / `lazyLibs` / `shaders` に列挙されている各ソースが何をしているかをまとめます。特に、通信を行う箇所、通信で得たバイナリを worker に渡す箇所、worker からメインスレッドへ結果を返す箇所を分けて説明します。

## 全体像

`gulpfile.js` はビルド時に次の3種類の資産を `build/` に配置します。

- `workers`: 複数の JavaScript ファイルを結合して `build/potree/workers/*.js` に出力する。点群データの展開、デコード、GPU 用バッファ生成を Web Worker 側で行うためのコード。
- `lazyLibs`: `build/potree/lazylibs/*` にコピーする。GeoPackage のように必要になったときだけ `Utils.loadScript()` で読み込む外部ライブラリ。
- `shaders`: GLSL ファイルを文字列化し、`build/shaders/shaders.js` の `Shaders["ファイル名"]` に格納する。点群描画、EDL、weighted splats の正規化などに使う。

重要な点は、`workers` に列挙された worker 自体は主に「受け取ったバイナリを変換して `postMessage()` で返す」役割で、HTTP 通信そのものは多くの場合 worker の呼び出し元 loader が担当していることです。

## 通信経路の要約

### Web Worker 生成とスレッド間通信

worker の生成は `src/WorkerPool.js` の `getWorker(url)` が担当します。

- `new Worker(url)` で worker スクリプトを起動する。
- 使い終わった worker は `returnWorker(url, worker)` で pool に戻す。
- メインスレッドから worker へは `worker.postMessage(message, transferables)` で `ArrayBuffer` を transfer する。
- worker 側は `onmessage = ...` で受け取り、処理後に `postMessage(message, transferables)` で戻す。

この `postMessage` はブラウザ内のスレッド間通信であり、ネットワーク通信ではありません。ただし点群データは大きいため、コピーではなく transferable として所有権を移す設計になっています。

### HTTP / ファイル取得を担当する主な箇所

対象 worker 群に関係する通信は、主に次の loader 側にあります。

- `src/loader/LasLazLoader.js`
  - LAS/LAZ データを読み込み、`LASDecoderWorker.js` に渡して GPU 用属性バッファへ変換する。
- `src/loader/ept/LaszipLoader.js`
  - EPT LASzip では `${base}/ept-data/<key>.laz` を `fetch()` で取得する。
  - COPC では `node.owner.getter(offset, offset + length)` で必要なバイト範囲を取得してから `EptLaszipDecoderWorker.js` に渡す。
- `src/loader/ept/BinaryLoader.js`
  - EPT binary では `XMLHttpRequest` で `<node>.bin` を `arraybuffer` として取得し、`EptBinaryDecoderWorker.js` に渡す。
- `src/loader/ept/ZstandardLoader.js`
  - EPT zstandard では拡張子を `.zst`、worker を `EptZstandardDecoderWorker.js` に差し替える。通信の基本形は `BinaryLoader` と同じ。
- `src/PointCloudEptGeometry.js`
  - EPT hierarchy page を `${base}/ept-hierarchy/<key>.json` から `fetch()` する。
- `src/modules/loader/2.0/OctreeLoader.js`
  - Potree 2.0 形式の `metadata.json`、`octree.bin`、`hierarchy.bin` を `fetch()` する。
  - `octree.bin` と `hierarchy.bin` は `Range: bytes=...` ヘッダー付きで必要範囲だけを取得する。
- `src/loader/GeoPackageLoader.js`
  - GeoPackage URL を `fetch(url)` で取得する。
  - `geopackage.js` と `sql-wasm.js` は `Utils.loadScript()` で遅延ロードする。
  - `sql-wasm.wasm` は `initSqlJs({ locateFile: ... })` から読み込まれる。
- `src/XHRFactory.js`
  - `XMLHttpRequest` 生成を共通化する。
  - `customHeaders` を設定すると、`xhr.open()` 後に任意ヘッダーを付けられる。

## workers

### LASLAZWorker

ビルド対象:

- `libs/plasio/workers/laz-perf.js`
- `libs/plasio/workers/laz-loader-worker.js`

出力先:

- `build/potree/workers/LASLAZWorker.js`

役割:

`LASLAZWorker` は LAZ 圧縮データを LAS 点レコードへ展開する worker です。`laz-perf.js` は Emscripten で生成された LAZ 展開ライブラリで、`Module.LASZip` などの API を提供します。`laz-loader-worker.js` はその API を worker メッセージ形式に包みます。

`libs/plasio/workers/laz-loader-worker.js` のメッセージ種別:

- `open`
  - メインスレッドから渡された `arraybuffer` を `Module._malloc()` した WASM/asm.js 側メモリにコピーする。
  - `new Module.LASZip()` を作り、`instance.open()` で LAZ データを開く。
- `header`
  - LAS ヘッダーを手動で読み、点数、点フォーマット、点レコード長、scale、offset、bounds を返す。
- `read`
  - `instance.getPoint()` で点を順番に展開する。
  - `skip` を使って間引きながら `ArrayBuffer` に格納する。
  - 展開済み点レコードを transferable として `postMessage()` で返す。
- `close`
  - `Module._free()` と `instance.delete()` で解放する。

通信観点:

- この worker 自体は HTTP 通信を行いません。
- 通信は「メインスレッドとの `postMessage`」です。
- LAZ ファイルの取得は loader 側が行い、取得済み `ArrayBuffer` が worker に渡されます。
- `laz-perf.js` は Emscripten 生成コードなので、実行環境によっては WASM/asm.js 内部初期化処理を持ちますが、このビルドでは `gulpfile.js` が `libs/copc/laz-perf.wasm` を `build/potree/workers` にコピーしています。

### LASDecoderWorker

ビルド対象:

- `src/workers/LASDecoderWorker.js`

出力先:

- `build/potree/workers/LASDecoderWorker.js`

役割:

`LASDecoderWorker` は、展開済み LAS 点レコードを Potree / Three.js が扱いやすい属性バッファに変換します。LAZ 展開は担当せず、既に `ArrayBuffer` として渡された点レコードを `DataView` で読む worker です。

主な処理:

- `onmessage = readUsingDataView`
- 入力:
  - `buffer`
  - `numPoints`
  - `pointSize`
  - `pointFormatID`
  - `scale`
  - `offset`
  - `mins`
- 各点について次を抽出する。
  - 位置: LAS の int32 XYZ に scale / offset を適用し、node 最小値を引いてローカル座標化する。
  - intensity
  - classification
  - return number
  - number of returns
  - point source ID
  - RGB 色。点フォーマット 2 の場合は 16bit 色を 8bit 相当に落とす。
- `tightBoundingBox`、`mean`、属性ごとの range を計算する。
- `position`、`color`、`intensity`、`classification`、`indices` などの `ArrayBuffer` を transferable で返す。

通信観点:

- HTTP 通信はありません。
- `postMessage()` による worker 間ではなく、メインスレッドと worker のスレッド間通信だけです。
- 呼び出し元は `src/loader/LasLazLoader.js` で、`Potree.scriptPath + '/workers/LASDecoderWorker.js'` を `WorkerPool` から取得します。

### EptLaszipDecoderWorker

ビルド対象:

- `libs/copc/index.js`
- `src/workers/EptLaszipDecoderWorker.js`

出力先:

- `build/potree/workers/EptLaszipDecoderWorker.js`

役割:

EPT の LASzip データ、または COPC の LAZ chunk を展開して、Potree 用の属性バッファへ変換します。`libs/copc/index.js` は COPC/LAS/EPT のヘッダー解析、VLR/ExtraBytes、LAZ chunk 展開、LAS View 生成などを提供する bundle です。

`src/workers/EptLaszipDecoderWorker.js` の流れ:

1. `event.data` から `isFullFile`、`compressed`、`header`、`eb`、`pointCount`、`nodemin` を受け取る。
2. `isFullFile` が true の場合は `Copc.Las.PointData.decompressFile()`、false の場合は `decompressChunk()` で展開する。
3. `Copc.Las.View.create(buffer, header, eb)` で LAS の各次元にアクセスする getter を作る。
4. 位置、色、intensity、classification、return number、number of returns、source id、GPS time を抽出する。
5. 16bit 色は必要に応じて 8bit へ正規化する。
6. GPS time は 64bit 値から最小値を引いた 32bit float へ変換し、`gpsMeta` に offset/range を保存する。
7. `postMessage(message, Object.values(buffers))` で返す。

通信観点:

- worker 自体は HTTP 通信を行いません。
- EPT `.laz` の取得は `src/loader/ept/LaszipLoader.js` の `fetch(url)` が担当します。
- COPC chunk の取得は `CopcLaszipLoader` が `node.owner.getter(pointDataOffset, pointDataOffset + pointDataLength)` を呼び、必要範囲の圧縮バイト列を取得します。
- worker には取得済み圧縮バイト列だけが渡されます。

### EptBinaryDecoderWorker

ビルド対象:

- `libs/ept/ParseBuffer.js`
- `src/workers/EptBinaryDecoderWorker.js`

出力先:

- `build/potree/workers/EptBinaryDecoderWorker.js`

役割:

EPT binary 形式の点データを Potree 用属性バッファへ変換します。`src/workers/EptBinaryDecoderWorker.js` は非常に薄く、`onmessage` で `parseEpt(event)` を呼ぶだけです。実体は `libs/ept/ParseBuffer.js` にあります。

`libs/ept/ParseBuffer.js` の主な処理:

- `event.data.schema` から次元名、型、サイズを読み取る。
- schema の順番から各次元の byte offset を計算する。
- `signed` / `unsigned` / `float` と size に応じて `DataView` の getter を選ぶ。
- `X/Y/Z` があれば position buffer を作る。
- `Red/Green/Blue` があれば color buffer を作る。
- `Intensity`、`Classification`、`ReturnNumber`、`NumberOfReturns`、`PointSourceId` があれば個別 buffer を作る。
- `scale`、`offset`、`mins` を使って位置をローカル座標化する。
- 16bit 色かどうかを走査して、必要なら 8bit へ正規化する。
- `tightBoundingBox`、`mean`、`indices` を作る。
- transferable で結果を返す。

通信観点:

- worker 自体は HTTP 通信を行いません。
- EPT binary の取得は `src/loader/ept/BinaryLoader.js` が担当します。
- `BinaryLoader` は `XHRFactory.createXMLHttpRequest()` で XHR を作り、`responseType = 'arraybuffer'` として `<node>.bin` を取得します。
- 取得後に `worker.postMessage(message, [message.buffer])` で worker に渡します。

### EptZstandardDecoderWorker

ビルド対象:

- `src/workers/EptZstandardDecoder_preamble.js`
- `libs/zstd-codec/bundle.js`
- `libs/ept/ParseBuffer.js`
- `src/workers/EptZstandardDecoderWorker.js`

出力先:

- `build/potree/workers/EptZstandardDecoderWorker.js`

役割:

EPT zstandard 圧縮データを展開し、その後は EPT binary と同じ `parseEpt(event)` で属性バッファへ変換します。

各ファイルの役割:

- `src/workers/EptZstandardDecoder_preamble.js`
  - worker 内で `zstd-codec` が期待する `window` / `document` を最低限用意する。
- `libs/zstd-codec/bundle.js`
  - Zstandard 圧縮/展開ライブラリ。
  - `window.ZstdCodec.run(resolve)` で codec を初期化する。
- `libs/ept/ParseBuffer.js`
  - 展開後の EPT binary を属性バッファに変換する。
- `src/workers/EptZstandardDecoderWorker.js`
  - `new zstd.Streaming()` を作り、`streaming.decompress(arr)` で `event.data.buffer` を展開する。
  - `event.data.buffer = decompressed.buffer` に差し替え、`parseEpt(event)` を呼ぶ。

通信観点:

- worker 自体は HTTP 通信を行いません。
- `src/loader/ept/ZstandardLoader.js` は `EptBinaryLoader` を継承し、拡張子を `.zst` に、worker path を `EptZstandardDecoderWorker.js` に変えるだけです。
- 実際の `.zst` 取得は `BinaryLoader` の XHR が行います。
- `zstd-codec` bundle の内部には WASM/asm.js 初期化のためのロード処理があります。これは codec の実装依存で、Potree 側の点群データ取得とは別のライブラリ初期化です。

## lazyLibs

### geopackage

ビルド対象:

- `libs/geopackage`

出力先:

- `build/potree/lazylibs/geopackage`

役割:

GeoPackage ファイルをブラウザ上で読み、features を Three.js の scene node に変換するためのライブラリです。Potree 側の入口は `src/loader/GeoPackageLoader.js` です。

`GeoPackageLoader` の処理:

- `loadUrl(url, params)`
  - `geopackage.js` と `sql-wasm.js` を `Utils.loadScript()` で読み込む。
  - `fetch(url)` で GeoPackage ファイル本体を取得する。
  - `arrayBuffer()` にして `loadBuffer()` に渡す。
- `loadBuffer(buffer, params)`
  - `initSqlJs({ locateFile: filename => wasmPath })` で `sql-wasm.wasm` の場所を指定する。
  - `geopackage.open(u8)` で GeoPackage を開く。
  - feature table を走査し、Point / LineString / Polygon を Three.js object に変換する。

通信観点:

- GeoPackage 本体の通信は `fetch(url)`。
- ライブラリ本体の読み込みは `Utils.loadScript()` による script load。
- SQLite WASM の読み込みは `initSqlJs()` の `locateFile` が指す `build/potree/lazylibs/sql.js/sql-wasm.wasm`。
- 外部 URL を `loadUrl()` に渡すとブラウザは外部サーバーへアクセスするため、CORS の影響を受けます。

### sql.js

ビルド対象:

- `libs/sql.js`

出力先:

- `build/potree/lazylibs/sql.js`

役割:

SQLite を WebAssembly / JavaScript で実行するライブラリです。GeoPackage は内部的に SQLite なので、ブラウザで `.gpkg` を読むために使われます。

主なファイル:

- `sql-wasm.js`
  - JavaScript 側の初期化 API、`initSqlJs()` を提供する。
- `sql-wasm.wasm`
  - SQLite 実装本体の WASM。

通信観点:

- Potree の `GeoPackageLoader` は `sql-wasm.js` を lazy script として読み込みます。
- `sql-wasm.wasm` は `initSqlJs()` 実行時にロードされます。
- DB の読み書きはブラウザメモリ上で行われ、サーバーへクエリを送る仕組みではありません。

## shaders

shader は GPU 上で動く GLSL コードです。HTTP 通信、XHR、fetch、WebSocket、worker `postMessage` は行いません。通信観点では、ビルド時に `build/shaders/shaders.js` へ文字列として埋め込まれ、実行時に WebGL shader としてコンパイルされるだけです。

### pointcloud.vs

点群描画の中心となる vertex shader です。

主な役割:

- LAS/EPT/Octree loader が作った属性を受け取る。
  - `position`
  - `color`
  - `intensity`
  - `classification`
  - `returnNumber`
  - `numberOfReturns`
  - `pointSourceID`
  - `indices`
  - `spacing`
  - `gpsTime`
  - `normal`
  - `aExtra`
- camera / model / projection 行列で点を clip space へ変換する。
- `visibleNodes` texture を使い、octree の可視 node 情報から LOD を推定する。
- fixed / attenuated / adaptive point size を切り替える。
- elevation、intensity、classification、return number、source id、GPS time、extra attribute などの色付けに必要な値を作る。
- clip box / clip sphere / clip polygon による表示・非表示・ハイライト条件を扱う。
- fragment shader へ `vColor`、`vLogDepth`、`vViewPosition`、`vRadius`、`vPointSize` などを渡す。

通信観点:

- 通信処理はありません。
- `visibleNodes`、`gradient`、`classificationLUT` などは CPU 側で用意された texture/uniform を読むだけです。

### pointcloud.fs

点群描画の fragment shader です。

主な役割:

- vertex shader から渡された `vColor` を最終色にする。
- point shape を切り替える。
  - square
  - circle
  - paraboloid
- circle shape では `gl_PointCoord` から点円外を `discard` する。
- paraboloid shape では fragment depth を補正し、球状に近い点表現を作る。
- EDL 用に alpha に logarithmic depth を格納する。
- weighted splats では点中心からの距離で weight を作り、色と alpha に反映する。

通信観点:

- 通信処理はありません。
- depth や color を framebuffer へ出力する GPU 処理です。

### pointcloud_sm.vs

shadow map / depth 系の点群描画向け vertex shader です。

主な役割:

- 点の view space depth を計算する。
- adaptive point size 用に octree 可視 node texture を参照して LOD を推定する。
- shadow/depth 用の点サイズを計算する。

注意:

このファイル内には `vViewPosition`、`vRadius`、`size`、`minSize`、`maxSize`、`fov` などを使う記述があります。実際の利用時は `PointCloudMaterial` 側の define や shader 組み立てとセットで評価する必要があります。

通信観点:

- 通信処理はありません。

### pointcloud_sm.fs

shadow map / depth 系の点群描画向け fragment shader です。

主な役割:

- `vLinearDepth` を色成分に書き出す。
- depth 可視化または shadow/depth pass 用の中間出力として使われる。

通信観点:

- 通信処理はありません。

### normalize.vs

fullscreen quad などの後処理用 vertex shader です。

主な役割:

- `position` と `uv` を受け取り、`vUv` を fragment shader へ渡す。
- `projectionMatrix * modelViewMatrix` で screen space の quad を描画する。

通信観点:

- 通信処理はありません。

### normalize.fs

weighted splats の accumulation 結果を正規化する fragment shader です。

主な役割:

- `uWeightMap` から accumulated color / weight を読む。
- `uDepthMap` から depth を読む。
- depth が背景なら `discard` する。
- `color = color / color.w` で weight 正規化する。
- `gl_FragDepthEXT = depth` で depth buffer を復元する。

通信観点:

- 通信処理はありません。
- GPU texture 間の後処理です。

### normalize_and_edl.fs

weighted splats の正規化と EDL を同時に行う fragment shader です。

主な役割:

- `uWeightMap` を weight 正規化する。
- `uEDLMap` の alpha に入った depth を近傍 sample と比較し、EDL の shade を計算する。
- `uDepthMap` の depth を `gl_FragDepthEXT` に戻す。
- EDL により輪郭・奥行き感を強調する。

通信観点:

- 通信処理はありません。

### edl.vs

EDL 後処理用 vertex shader です。

主な役割:

- screen quad の `uv` を `vUv` として渡す。
- 後段の `edl.fs` が画面全体の color/depth texture を読むための座標を作る。

通信観点:

- 通信処理はありません。

### edl.fs

Eye-Dome Lighting の fragment shader です。

主な役割:

- `uEDLColor` の RGB と alpha depth を読む。
- 周辺 pixel の depth と比較し、奥行き差が大きい箇所を暗くする。
- `edlStrength` と `radius` で効果の強さとサンプル距離を制御する。
- alpha に格納された logarithmic depth を通常 depth に戻して `gl_FragDepthEXT` に書く。
- depth がない pixel は `discard` する。

通信観点:

- 通信処理はありません。
- 画面上の texture を読む GPU 後処理です。

### blur.vs

blur 後処理用 vertex shader です。

主な役割:

- screen quad の `uv` を `vUv` として渡す。
- fragment shader が周辺 pixel を読むための座標を作る。

通信観点:

- 通信処理はありません。

### blur.fs

単純な 3x3 平均 blur の fragment shader です。

主な役割:

- `screenWidth` / `screenHeight` から 1 pixel 分の `dx` / `dy` を計算する。
- `map` texture の周囲 9 点を読み、平均して出力する。

通信観点:

- 通信処理はありません。

## 通信系をつかさどる箇所の詳細

### 1. Potree 2.0 octree loader

ファイル:

- `src/modules/loader/2.0/OctreeLoader.js`

通信:

- `fetch(url)` で metadata JSON を取得する。
- `fetch(urlOctree, { headers: { Range: 'bytes=first-last' } })` で `octree.bin` の必要範囲だけを取得する。
- `fetch(hierarchyPath, { headers: { Range: 'bytes=first-last' } })` で `hierarchy.bin` の必要範囲だけを取得する。

worker 連携:

- 取得した `ArrayBuffer` を `DecoderWorker.js` または `DecoderWorker_brotli.js` に渡す。
- worker から返った属性 buffer を `THREE.BufferGeometry` に設定する。

この経路は、巨大な点群を一括取得せず、表示に必要な node のバイト範囲だけ読むための通信制御を担っています。

### 2. EPT hierarchy / data loader

ファイル:

- `src/PointCloudEptGeometry.js`
- `src/loader/ept/LaszipLoader.js`
- `src/loader/ept/BinaryLoader.js`
- `src/loader/ept/ZstandardLoader.js`

通信:

- hierarchy:
  - `${base}/ept-hierarchy/<key>.json` を `fetch()` で取得する。
- EPT LASzip:
  - `${base}/ept-data/<key>.laz` を `fetch()` で取得する。
- EPT binary:
  - `<node>.bin` を XHR で取得する。
- EPT zstandard:
  - `<node>.zst` を XHR で取得する。

worker 連携:

- LASzip は `EptLaszipDecoderWorker.js`。
- binary は `EptBinaryDecoderWorker.js`。
- zstandard は `EptZstandardDecoderWorker.js`。

この経路では、データ形式ごとに loader が通信対象の拡張子と worker を切り替えます。実際の解析・展開は worker 側に逃がして、UI スレッドの停止を避けています。

### 3. COPC LASzip loader

ファイル:

- `src/loader/ept/LaszipLoader.js`
- `libs/copc/index.js`

通信:

- COPC の場合、点データはファイル全体ではなく、node の `pointDataOffset` と `pointDataLength` から必要な chunk だけ取得されます。
- `CopcLaszipLoader` は `node.owner.getter(begin, end)` を使います。
- `libs/copc/index.js` には COPC hierarchy page や point data buffer を byte range で取得するための getter 抽象があります。

worker 連携:

- 取得した圧縮 chunk を `EptLaszipDecoderWorker.js` に渡す。
- worker 側で `decompressChunk()` を実行する。

この経路も、巨大な COPC ファイルを一括取得しないための通信制御が中心です。

### 4. GeoPackage loader

ファイル:

- `src/loader/GeoPackageLoader.js`

通信:

- `Utils.loadScript()` で lazy lib を読み込む。
- `fetch(url)` で `.gpkg` 本体を取得する。
- `initSqlJs()` が `sql-wasm.wasm` をロードする。

この経路は点群 worker とは別で、地物レイヤーを読み込むための通信です。GeoPackage 内の SQL はブラウザ内メモリで実行され、DB サーバーへ問い合わせるわけではありません。

### 5. XHRFactory

ファイル:

- `src/XHRFactory.js`

役割:

- `XMLHttpRequest` 生成を共通化する。
- `customHeaders` が設定されていれば、`open()` 呼び出し後にヘッダーを付与する。

通信上の意味:

- `Authorization` などのカスタムヘッダーをここに設定すると、Potree の XHR 系 loader に影響する可能性があります。
- 既定値では `customHeaders` は null 相当で、追加ヘッダーは送られません。
- `withCredentials` の設定値は存在しますが、この実装では生成した XHR に `xhr.withCredentials = ...` を代入していません。Cookie 等を明示的に含める制御は、このファイルの現状コードだけでは完結していません。

## ファイル別まとめ

| 区分 | ファイル | 役割 | 通信の有無 |
|---|---|---|---|
| worker lib | `libs/plasio/workers/laz-perf.js` | LAZ 展開用 Emscripten 生成ライブラリ | ライブラリ初期化内部を除き、点群取得通信はしない |
| worker | `libs/plasio/workers/laz-loader-worker.js` | LAZ を開く、ヘッダー読む、点を展開する | HTTP なし、`postMessage` あり |
| worker | `src/workers/LASDecoderWorker.js` | LAS 点レコードを Potree 属性バッファへ変換 | HTTP なし、`postMessage` あり |
| worker lib | `libs/copc/index.js` | COPC/LAS/EPT 解析・LAZ chunk 展開 API | getter 抽象あり。実際の取得は呼び出し側 |
| worker | `src/workers/EptLaszipDecoderWorker.js` | EPT/COPC LASzip を展開して属性バッファ化 | HTTP なし、`postMessage` あり |
| worker lib | `libs/ept/ParseBuffer.js` | EPT binary を schema に従って属性バッファ化 | HTTP なし、`postMessage` あり |
| worker | `src/workers/EptBinaryDecoderWorker.js` | `parseEpt(event)` を呼ぶ thin wrapper | HTTP なし、`postMessage` あり |
| worker lib | `libs/zstd-codec/bundle.js` | Zstandard 展開ライブラリ | codec 初期化内部ロードあり得る。点群取得通信はしない |
| worker | `src/workers/EptZstandardDecoder_preamble.js` | zstd bundle 用の `window` / `document` stub | 通信なし |
| worker | `src/workers/EptZstandardDecoderWorker.js` | `.zst` を展開して `parseEpt()` へ渡す | HTTP なし、`postMessage` あり |
| lazy lib | `libs/geopackage` | GeoPackage 読み取り | `GeoPackageLoader` から script load される |
| lazy lib | `libs/sql.js` | SQLite WASM | `sql-wasm.js` / `sql-wasm.wasm` を lazy load |
| shader | `src/materials/shaders/pointcloud.vs` | 点群 vertex shader | 通信なし |
| shader | `src/materials/shaders/pointcloud.fs` | 点群 fragment shader | 通信なし |
| shader | `src/materials/shaders/pointcloud_sm.vs` | shadow/depth 用 vertex shader | 通信なし |
| shader | `src/materials/shaders/pointcloud_sm.fs` | shadow/depth 用 fragment shader | 通信なし |
| shader | `src/materials/shaders/normalize.vs` | 後処理 quad vertex shader | 通信なし |
| shader | `src/materials/shaders/normalize.fs` | weighted splats 正規化 | 通信なし |
| shader | `src/materials/shaders/normalize_and_edl.fs` | 正規化 + EDL | 通信なし |
| shader | `src/materials/shaders/edl.vs` | EDL quad vertex shader | 通信なし |
| shader | `src/materials/shaders/edl.fs` | EDL fragment shader | 通信なし |
| shader | `src/materials/shaders/blur.vs` | blur quad vertex shader | 通信なし |
| shader | `src/materials/shaders/blur.fs` | 3x3 平均 blur | 通信なし |

## 実装を読むときの入口

通信を確認したい場合は、worker ファイルからではなく次の順に読むと追いやすいです。

1. `gulpfile.js`
   - どの worker / lazy lib / shader がどこへ配置されるか。
2. `src/WorkerPool.js`
   - worker の生成と再利用。
3. `src/loader/ept/*.js`、`src/modules/loader/2.0/OctreeLoader.js`、`src/loader/GeoPackageLoader.js`
   - HTTP / XHR / range request の実体。
4. `src/workers/*.js`、`libs/ept/ParseBuffer.js`
   - 取得済みバイナリを属性バッファへ変換する実体。
5. `src/materials/shaders/*.vs` / `*.fs`
   - 変換済み属性が GPU 上でどう描画されるか。
