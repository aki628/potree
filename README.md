# Potree（このリポジトリ）日本語 README

このリポジトリは、WebGL ベースの点群ビューア **Potree** の開発用ソースです。
本 README は、ローカルでの環境構築と、`data/sample.las` の実行確認手順に絞って日本語でまとめています。

## 1. 概要

- 大規模点群をブラウザで表示するためのビューア
- `npm start` でビルド監視 + ローカルサーバ起動
- 追加サンプル: `examples/sample_las_top_view.html`
  - `data/sample.las` を読み込み
  - 自作平面（`custom_base_plane`）を追加
  - トップビュー（上面表示）で表示
  - 既定で全点描画モード（`maxPoints=0`, `maxReadPoints=0`）

## 2. 必要環境

- Node.js 18 系推奨
- npm 9 系推奨

確認:

```bash
node -v
npm -v
```

## 3. 環境構築手順

リポジトリ直下で実行します。

```bash
npm install
```

補足:

- 依存パッケージをインストール
- `postinstall` で `npm run build` が実行され、`build/potree/` が生成されます

## 4. 開発サーバ起動

```bash
npm start
```

起動後:

- Examples 一覧: `http://localhost:1234/examples/`

## 5. サンプルコードの実行方法

### 5.1 標準サンプル

- `http://localhost:1234/examples/viewer.html`

### 5.2 `sample.las` サンプル

- `http://localhost:1234/examples/sample_las_top_view.html`

既定値（全点描画）:

- `maxPoints=0`（描画点数上限なし）
- `maxReadPoints=0`（読み取り上限なし）

主なクエリパラメータ:

- `file`: 読み込む LAS パス（既定: `../data/sample.las`）
- `maxPoints`: 描画点数上限（`0` で全点）
- `maxReadPoints`: 読み取り点数上限（`0` で全件）
- `chunkPoints`: 1チャンクあたり点数（既定: `1000000`）
- `pointSize`: 点サイズ

負荷を抑えたい例:

```text
http://localhost:1234/examples/sample_las_top_view.html?maxPoints=3000000&maxReadPoints=3000000&chunkPoints=500000&pointSize=0.015
```

## 6. 完了条件（今回の要件）

以下を満たせば完了です。

1. `data/sample.las` をレンダリングできる
2. 点群と自作平面（`custom_base_plane`）を同時表示できる
3. トップビュー（上面表示）で確認できる
4. 全点モード（`maxPoints=0&maxReadPoints=0`）で `seen==rendered` が `yes` になる

## 7. よく使うコマンド

```bash
npm install      # 依存インストール
npm run build    # 手動ビルド
npm start        # 監視 + ローカルサーバ
```

## 8. トラブルシュート

- `npm install` が失敗する（ネットワーク系）
  - 時間をおいて再試行
- `sample.las` が重い
  - `maxReadPoints` を小さくする（例: `2000000`）
  - `maxPoints` を小さくする
  - `chunkPoints` を小さくする（例: `300000`）
- 画面が見づらい
  - `pointSize` を調整

## 9. 関連ドキュメント

- ADR: [docs/adr/0001-las-full-rendering.md](docs/adr/0001-las-full-rendering.md)
- 詳細手順書: [docs/sample-las-setup-ja.md](docs/sample-las-setup-ja.md)
- 公式 Potree リポジトリ: <https://github.com/potree/potree>
- PotreeConverter: <https://github.com/potree/PotreeConverter>
