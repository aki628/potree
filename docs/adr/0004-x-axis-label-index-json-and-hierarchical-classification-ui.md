# ADR 0004: X軸区間ごとのラベル索引JSONとClassification階層UI

- Status: Accepted
- Date: 2026-04-20

## Context

現状の Classification UI はクラス項目がフラットに並ぶ構造であり、
「Classification を親として、label 名を子として展開表示する」階層操作ができない。

また、点群の位置関係を利用したラベル単位の解析データとして、
X軸方向の区間分割ごとに point index を集約した JSON が存在しない。

要件は以下。

1. 点群を X軸で区間分割し、各区間で `{label名: indexes}` を JSON 化する
2. Classification UI を親子階層化し、親の近くの下矢印で子 label のチェックボックスを開閉する

## Decision

1. `scripts/generate_sample_las_label_indexes_by_x.py` を追加する
- 入力: `data/sample.las`, `data/sample_labels.xml`
- 処理: X軸 min/max から等間隔ビンを作成し、各 point をビンへ割り当てる
- 出力: 区間ごとに `{label名: [pointIndex, ...]}` を保持する JSON

2. 出力JSONは `data/sample_label_indexes_by_x.json` を既定とする
- ルートにはメタ情報（軸, 区間数, スキャン点数）を持つ
- 本体は `intervals` 配列に区間情報と `labelIndexes`（辞書）を持つ

3. `src/viewer/sidebar.js` の Classification リストを階層化する
- 親行: Classification チェックボックス + 展開矢印
- 子行: label 名（既存 classification 名）の個別チェックボックス
- 親チェック: 全 label の表示/非表示切替
- 子チェック: 該当 label のみ表示/非表示切替

## Consequences

### Positive

- 空間区間（X軸）と label の対応を index レベルで参照できる
- UI が階層的になり、多数 label の表示制御がしやすくなる

### Negative

- JSON は点数に比例して大きくなる
- 階層 UI 実装に伴い、Classification リスト更新ロジックが複雑化する

## Completion Criteria

以下をすべて満たしたら完了とする。

1. `docs/adr/0004-x-axis-label-index-json-and-hierarchical-classification-ui.md` が追加されている
2. `scripts/generate_sample_las_label_indexes_by_x.py` が追加され、`data/sample.las` から JSON を生成できる
3. 生成 JSON が区間ごとに `{label名: indexes}` を保持している
4. `src/viewer/sidebar.js` の Classification UI に親行の展開矢印があり、クリックで子 label チェックボックスが開閉する
5. 親チェックボックスで全 label を一括切替できる
6. 子 label チェックボックスで個別切替でき、既存の classification 可視性反映が維持される
7. `npm run build` が成功する

## Verification Plan

1. `python3 scripts/generate_sample_las_label_indexes_by_x.py --help` が表示される
2. 生成 JSON を確認し、`intervals[].labelIndexes` が辞書で、値が index 配列であることを確認する
3. ビューアで Classification セクションの矢印開閉と親子チェックボックス動作を確認する
4. `npm run build` 成功を確認する
