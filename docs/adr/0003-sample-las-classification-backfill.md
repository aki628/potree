# ADR 0003: sample.las の Classification を付与してラベル切替を実動作させる

- Status: Accepted
- Date: 2026-04-19

## Context

`examples/sample_las_top_view.html` は classification を読んでラベル別表示/非表示を切り替える実装を持つが、
`data/sample.las` の classification が全点 `0` のため、実運用上はラベル切替の意味が出ていない。

実測では `data/sample.las`（LAS 1.4 / Point Format 7 / 43,030,981 points）の
classification 分布は `0: 43,030,981` のみであった。

## Decision

1. `data/sample.las` に対して classification をバックフィルする
- Point Format 7 の classification オフセット `16` へ書き込む
- 全点を対象に、Z 値の相対位置（min-max 正規化）で 5 区分する

2. 分類ルールは以下とする（暫定可視化ルール）
- `0.0 <= zNorm < 0.2` -> class `2` (Ground)
- `0.2 <= zNorm < 0.4` -> class `3` (Low Vegetation)
- `0.4 <= zNorm < 0.6` -> class `4` (Medium Vegetation)
- `0.6 <= zNorm < 0.8` -> class `5` (High Vegetation)
- `0.8 <= zNorm <= 1.0` -> class `6` (Building)

3. 付与処理は再実行可能なスクリプトとして管理する
- `scripts/backfill_sample_las_classification.py` を追加する
- スクリプト実行後、`examples/sample_las_top_view.html` のラベル UI で複数ラベルが操作可能であることを確認する

## Consequences

### Positive

- ラベル別表示/非表示が実データで機能する
- ラベル別色分け UI の確認が可能になる
- 処理をスクリプト化することで再現性が担保できる

### Negative

- Classification は元データ由来でなく、可視化検証のためのヒューリスティック付与となる
- 元 LAS の classification 情報（全 0）を上書きする

## Completion Criteria

以下をすべて満たしたら完了とする。

1. `docs/adr/0003-sample-las-classification-backfill.md` が追加されている
2. `scripts/backfill_sample_las_classification.py` が追加され、`data/sample.las` へ分類を書き込める
3. `data/sample.las` の classification 分布が複数クラス（少なくとも `2-6`）になる
4. `examples/sample_las_top_view.html` の Labels パネルに複数ラベルが表示される前提が満たされる
5. ラベル単位の表示/非表示切替と色変更が動作する（既存機能の維持）
6. `npm run build` が成功する

## Verification Plan

- classification 分布を集計し、`2-6` の各クラスに点数が存在すること
- `sample_las_top_view.html` 起動時のラベル数が 1 ではなく複数であること
- `npm run build` 成功
