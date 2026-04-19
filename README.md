# Potree（このリポジトリ）日本語 README

このリポジトリは、WebGL ベースの点群ビューア **Potree** の開発用ソースです。
本 README は、ローカルでの環境構築と、今回追加した `data/sample.las` の実行確認手順に絞って日本語でまとめています。

## 1. 概要

- 大規模点群をブラウザで表示するためのビューア
- `npm start` でビルド監視 + ローカルサーバ起動
- 追加サンプル: `examples/sample_ply_top_view.html`
  - `data/sample.las` を読み込み
  - 自作平面（`custom_base_plane`）を追加
  - トップビュー（上面表示）で表示

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

`npm start` が行うこと:

- ソース監視
- 変更時の自動ビルド
- `localhost:1234` で配信

## 5. サンプルコードの実行方法

### 5.1 標準サンプル

- `http://localhost:1234/examples/viewer.html`

### 5.2 今回の `sample.las` サンプル

- `http://localhost:1234/examples/sample_ply_top_view.html`

推奨パラメータ（初回確認）:

```text
http://localhost:1234/examples/sample_ply_top_view.html?maxPoints=1200000&maxReadPoints=8000000&pointSize=0.015
```

主なクエリパラメータ:

- `file`: 読み込む LAS パス（既定: `../data/sample.las`）
- `maxPoints`: 画面に保持する点数上限
- `maxReadPoints`: 読み取る頂点数上限（`0` で全件）
- `pointSize`: 点サイズ

## 6. 完了条件（今回の要件）

以下を満たせば完了です。

1. `data/sample.las` をレンダリングできる
2. 点群と自作平面（`custom_base_plane`）を同時表示できる
3. トップビュー（上面表示）で確認できる

判定の目安:

- 左上ステータスが `Completed`
- 表示中の点群に加えて半透明平面が見える
- `Top View` ボタンで上面視点に戻せる

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
  - `maxPoints` を下げる
- 表示が荒い / 密すぎる
  - `pointSize` を調整

## 9. 関連ドキュメント

- 詳細手順書: [docs/sample-las-setup-ja.md](docs/sample-las-setup-ja.md)
- 公式 Potree リポジトリ: <https://github.com/potree/potree>
- PotreeConverter: <https://github.com/potree/PotreeConverter>
