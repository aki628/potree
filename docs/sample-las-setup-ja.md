# Potree 実行環境構築手順（`data/sample.las` + 自作平面 + トップビュー）

この手順書は、ローカル環境で Potree を起動し、`data/sample.las` をレンダリングしたうえで、
自作の平面と点群を上面表示（トップビュー）できる状態を再現するためのものです。

## 1. 前提

- OS: Linux / macOS / Windows (WSL 含む)
- Node.js: 18 系（本リポジトリ検証時: `v18.19.0`）
- npm: 9 系（本リポジトリ検証時: `9.2.0`）
- リポジトリ直下に `data/sample.las` が存在すること

確認コマンド:

```bash
node -v
npm -v
ls -lh data/sample.las
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

## 5. `sample.las` + 平面 + トップビューの表示

### 5.1 専用ページ

- 直接URL: `http://localhost:1234/examples/sample_las_top_view.html`
- Examples 一覧から: `Sample LAS Top View`

### 5.2 既定パラメータ（全点モード）

- `maxPoints=0`（描画点数上限なし）
- `maxReadPoints=0`（読み取り上限なし）
- `chunkPoints=1000000`（1チャンクの点数）

### 5.3 パラメータ一覧

- `file`: 読み込む LAS ファイルパス
- `maxPoints`: 描画点数上限（`0` で全点）
- `maxReadPoints`: 読み取り点数上限（`0` で全件）
- `chunkPoints`: チャンク点数（大きいほどオブジェクト数は減るがメモリ圧が上がる）
- `pointSize`: 点サイズ

負荷を抑えたい場合の例:

```text
http://localhost:1234/examples/sample_las_top_view.html?maxPoints=3000000&maxReadPoints=3000000&chunkPoints=500000&pointSize=0.015
```

## 6. 完了条件

以下をすべて満たしたら完了です。

1. `data/sample.las` をレンダリングできること
- 判定方法: 左上ステータスが `Completed` になる。

2. 自作の平面と上記点群を同時表示できること
- 判定方法: 半透明平面（`custom_base_plane`）が表示される。

3. 上面表示（トップビュー）にできること
- 判定方法: 初期表示で上面視点になり、`Top View` で戻せる。

4. 全点モードで `seen==rendered` が一致すること
- 判定方法: `maxPoints=0&maxReadPoints=0` で `seen==rendered: yes` が表示される。

## 7. 完了条件を満たすまでの修正ループ

1. `npm run build` を再実行
2. ブラウザをハードリロード
3. 依然として重い場合は `chunkPoints` / `maxReadPoints` / `maxPoints` を調整
4. ブラウザコンソールを確認し、`examples/sample_las_top_view.html` を修正
5. 修正後に 1 へ戻る

## 8. トラブルシュート

- `EADDRINUSE: 1234`
  - 既存プロセスを停止して再起動
- 読み込みが遅い / メモリ負荷が高い
  - `chunkPoints` を小さくする
  - `maxReadPoints` / `maxPoints` に上限を設定する
- 画面が見づらい
  - `pointSize` を調整する

## 9. 関連ファイル

- `examples/sample_las_top_view.html`
- `docs/adr/0001-las-full-rendering.md`
- `examples/page.json`
- `examples/github.html`
