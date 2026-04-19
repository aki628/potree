# Potree 実行環境構築手順（`data/sample.las` + ラベル色分け + 自作平面 + トップビュー）

この手順書は、ローカル環境で Potree を起動し、`data/sample.las` をレンダリングしたうえで、
ラベル（classification）ごとの色分け、表示/非表示切替、色編集 UI、
自作の平面表示、上面表示（トップビュー）を再現するためのものです。

## 1. 前提

- OS: Linux / macOS / Windows (WSL 含む)
- Node.js: 18 系（本リポジトリ検証時: `v18.19.0`）
- npm: 9 系（本リポジトリ検証時: `9.2.0`）
- リポジトリ直下に `data/sample.las` が存在すること
- リポジトリ直下に `data/sample_labels.xml` が存在すること

確認コマンド:

```bash
node -v
npm -v
ls -lh data/sample.las data/sample_labels.xml
```

## 2. 依存関係インストール

```bash
npm install
```

`postinstall` で `npm run build` が実行され、`build/potree` が生成されます。

## 3. ビルド（必要時）

```bash
npm run build
```

## 4. サーバ起動

```bash
npm start
```

起動後、`http://localhost:1234/examples/` を開きます。

## 5. `sample.las` + ラベル + 平面 + トップビューの表示

### 5.1 専用ページ

- 直接URL: `http://localhost:1234/examples/sample_las_top_view.html`
- Examples 一覧から: `Sample LAS Top View`

### 5.2 既定パラメータ（全点モード）

- `maxPoints=0`（描画点数上限なし）
- `maxReadPoints=0`（読み取り上限なし）
- `chunkPoints=1000000`（1チャンクの点数）
- `labelMap=../data/sample_labels.xml`（ラベル定義 XML）

### 5.3 パラメータ一覧

- `file`: 読み込む LAS ファイルパス
- `labelMap`: ラベルカラーマップ XML のパス
- `maxPoints`: 描画点数上限（`0` で全点）
- `maxReadPoints`: 読み取り点数上限（`0` で全件）
- `chunkPoints`: チャンク点数（大きいほどオブジェクト数は減るがメモリ圧が上がる）
- `pointSize`: 点サイズ

### 5.4 `sample.las` の Classification 付与（初回のみ）

`data/sample.las` の classification が単一（例: 全 0）の場合は、以下で付与します。

```bash
python3 scripts/backfill_sample_las_classification.py --path data/sample.las --chunk-points 500000
```

処理後に class `2-6` が出ていることを確認します。

```bash
python3 scripts/backfill_sample_las_classification.py --path data/sample.las --dry-run
```

負荷を抑えたい場合の表示URL例:

```text
http://localhost:1234/examples/sample_las_top_view.html?maxPoints=3000000&maxReadPoints=3000000&chunkPoints=500000&pointSize=0.015
```

## 6. 完了条件

以下をすべて満たしたら完了です。

1. `data/sample.las` の classification が複数クラス（少なくとも class `2-6`）になっていること
- 判定方法: `scripts/backfill_sample_las_classification.py --dry-run` の Histogram で class `2-6` に点数がある。

2. `data/sample.las` をレンダリングできること
- 判定方法: 左上ステータスが `Completed` になる。

3. ラベルごとに色分け表示されること
- 判定方法: 同じラベルの点が同色で描画される。

4. ラベルごとの表示/非表示を切り替えられること
- 判定方法: 右上 Labels パネルのチェックボックスで対象ラベルが消える/再表示される。

5. ラベル色を UI で変更できること
- 判定方法: ラベル行の色ボタンをクリックし、選択色が即時描画に反映される。

6. 自作の平面と上記点群を同時表示できること
- 判定方法: 半透明平面（`custom_base_plane`）が表示される。

7. 上面表示（トップビュー）にできること
- 判定方法: 初期表示で上面視点になり、`Top View` で戻せる。

8. 全点モードで `seen==rendered` が一致すること
- 判定方法: `maxPoints=0&maxReadPoints=0` で `seen==rendered: yes` が表示される。

## 7. 完了条件を満たすまでの修正ループ

1. `python3 scripts/backfill_sample_las_classification.py --path data/sample.las` を実行
2. `npm run build` を再実行
3. ブラウザをハードリロード
4. 依然として重い場合は `chunkPoints` / `maxReadPoints` / `maxPoints` を調整
5. ラベル定義を変更したい場合は `data/sample_labels.xml` を修正して再読込
6. ブラウザコンソールを確認し、`examples/sample_las_top_view.html` を修正
7. 修正後に 1 へ戻る

## 8. トラブルシュート

- `EADDRINUSE: 1234`
  - 既存プロセスを停止して再起動
- 読み込みが遅い / メモリ負荷が高い
  - `chunkPoints` を小さくする
  - `maxReadPoints` / `maxPoints` に上限を設定する
- ラベル色が期待通りでない
  - `data/sample_labels.xml` の `color="#RRGGBB"` を確認
  - XML 読み込み失敗時はフォールバック色になる
- class が 1 種類のまま
  - `scripts/backfill_sample_las_classification.py` を再実行する
  - 対象ファイルが `data/sample.las` であることを確認する
- 画面が見づらい
  - `pointSize` を調整する

## 9. 関連ファイル

- `examples/sample_las_top_view.html`
- `data/sample_labels.xml`
- `scripts/backfill_sample_las_classification.py`
- `docs/adr/0001-las-full-rendering.md`
- `docs/adr/0002-label-color-map-and-visibility.md`
- `docs/adr/0003-sample-las-classification-backfill.md`
- `examples/page.json`
- `examples/github.html`
