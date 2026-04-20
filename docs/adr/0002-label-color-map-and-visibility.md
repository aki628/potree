# ADR 0002: LAS ラベル色分けとラベル単位の表示切替を追加する

- Status: Accepted
- Date: 2026-04-19

## Context

`examples/sample_las_top_view.html` は LAS 点群を全点表示できるが、以下が不足している。

- classification（ラベル）単位で色を定義して表示する機能
- ラベルごとの表示・非表示切替機能
- ラベル色を UI から変更する機能

要件では、色定義は `.xml` ファイルで管理し、アプリはそのカラーマップを読み込んで描画へ反映する必要がある。

## Decision

1. `data/sample_labels.xml` を新設し、ラベル定義を以下で管理する
- `id`: classification 値（0-255）
- `name`: UI 表示名
- `color`: `#RRGGBB`
- `visible`: 初期表示フラグ

2. `sample_las_top_view.html` は LAS レコードから classification を読み取り、ラベルごとに描画チャンクを分離する
- 各ラベルは独立した `THREE.PointsMaterial` を持ち、色変更を即時反映する
- ラベルグループの `visible` 切替で表示・非表示を制御する

3. ラベル UI パネルを追加する
- ラベル名表示
- 表示/非表示チェックボックス
- 色スウォッチ（クリックでカラーピッカーを開く）
- カラーピッカー変更時にそのラベル色を即時更新

4. XML に未定義の classification 値が LAS 内に存在した場合は、既定名 `Class <id>` と決定色（ハッシュ由来）で自動追加する

## Consequences

### Positive

- ラベルごとに意味を持った色で可視化できる
- 目的ラベルだけを残して解析できる
- 色は XML と UI の双方で運用できる

### Negative

- ラベル数が多いほど描画オブジェクト数と UI 要素数が増える
- ラベル単位のグループ分割により、単一色描画より管理コストが増える
- UI 変更した色はセッション内反映であり、XML へ自動保存はしない

## Completion Criteria

以下をすべて満たしたら完了とする。

1. `data/sample_labels.xml` が存在し、`id`/`name`/`color`/`visible` を持つラベル定義を含む
2. `examples/sample_las_top_view.html` が XML カラーマップを読み取り、classification ごとの色で点群を描画する
3. ラベル一覧 UI でラベル単位の表示・非表示を切り替えられる
4. ラベル一覧 UI の色スウォッチクリックで色を変更でき、変更が即時に描画へ反映される
5. XML 未定義ラベルが LAS 内に存在しても描画が継続し、ラベル一覧に表示される
6. 既存要件（`custom_base_plane` 表示、Top View、`maxPoints`/`maxReadPoints` 動作）が維持される
7. `npm run build` が成功する

## Verification Plan

- `npm run build` が成功すること
- `sample_las_top_view.html` を開き、以下を目視確認すること
1. ラベルごとに色が分かれている
2. チェックボックスで対象ラベルが表示・非表示になる
3. 色変更 UI で色を変えると即時反映される
4. Top View ボタンとベース平面表示が維持される
