# Potree 実行環境構築手順（`data/sample.ply` + 自作平面 + トップビュー）

この手順書は、ローカル環境で Potree を起動し、`data/sample.ply` をレンダリングしたうえで、
自作の平面と点群を上面表示（トップビュー）できる状態を再現するためのものです。

## 1. 前提

- OS: Linux / macOS / Windows (WSL 含む)
- Node.js: 18 系（本リポジトリ検証時: `v18.19.0`）
- npm: 9 系（本リポジトリ検証時: `9.2.0`）
- リポジトリ直下に `data/sample.ply` が存在すること

確認コマンド:

```bash
node -v
npm -v
ls -lh data/sample.ply
```

## 2. 依存関係インストール

```bash
npm install
```

`postinstall` で `npm run build` が実行され、`build/potree` が生成されます。

## 3. ビルド（必要時）

`examples/page.json` などを更新した後は再ビルドします。

```bash
npm run build
```

## 4. サーバ起動

```bash
npm start
```

起動後、`http://localhost:1234/examples/` を開きます。

## 5. `sample.ply` + 平面 + トップビューの表示

### 5.1 専用ページ

- 直接URL: `http://localhost:1234/examples/sample_ply_top_view.html`
- Examples 一覧から: `Sample PLY Top View`

### 5.2 推奨パラメータ

`sample.ply` は非常に大きいため、まずは以下で確認します。

- `maxPoints`: 画面に保持する点数上限
- `maxReadPoints`: 読み取る頂点数上限（0 で全件走査）
- `pointSize`: 描画点サイズ

初回確認例:

```text
http://localhost:1234/examples/sample_ply_top_view.html?maxPoints=1200000&maxReadPoints=8000000&pointSize=0.015
```

全件走査したい場合の例（時間がかかります）:

```text
http://localhost:1234/examples/sample_ply_top_view.html?maxPoints=1200000&maxReadPoints=0&pointSize=0.015
```

## 6. 完了条件

以下をすべて満たしたら完了です。

1. `data/sample.ply` をレンダリングできること
- 判定方法: 画面左上ステータスが `Completed` になり、`rendered: ...` が 0 より大きい。

2. 自作の平面と上記点群を同時表示できること
- 判定方法: 点群に加えて、半透明の平面（`custom_base_plane`）が表示される。

3. 上面表示（トップビュー）にできること
- 判定方法: 初期表示で上面視点になっていること。
- 補助確認: 左上 `Top View` ボタンで再度上面視点に戻せること。

## 7. 完了条件を満たすまでの修正ループ

完了条件未達の場合は、以下を順に実施して再確認します。

1. `npm run build` を再実行
2. ブラウザをハードリロード
3. `maxReadPoints` / `maxPoints` を減らして再確認
4. それでも失敗する場合はブラウザコンソールのエラーを確認し、`examples/sample_ply_top_view.html` を修正
5. 修正後に再度 1 へ戻る

## 8. トラブルシュート

- `EAI_AGAIN` などの npm ネットワークエラー:
  - 通信可能な環境で `npm install` を再試行
- 読み込みが遅い:
  - `maxReadPoints` を小さくする（例: `2000000`）
- 画面が点で埋まり過ぎる / 見づらい:
  - `pointSize` を `0.005` などへ調整

## 9. 関連ファイル

- `examples/sample_ply_top_view.html`
- `examples/page.json`
- `examples/github.html`
