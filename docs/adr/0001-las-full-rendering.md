# ADR 0001: LAS サンプルで全点描画を可能にする

- Status: Accepted
- Date: 2026-04-19

## Context

`examples/sample_las_top_view.html` では、以下の制約により「全点描画」ができない。

- `maxPoints` の既定値が `1,200,000` で、保持点数に上限がある
- `maxReadPoints` の既定値が `8,000,000` で、読み取り自体に上限がある
- 上限到達時は reservoir sampling によって置換されるため、全点を描画できない

今回の要件は「LAS 点群を全点描画できること」であり、既定動作として全点描画に対応する必要がある。

## Decision

1. `maxPoints=0` を「無制限（全点描画）」の意味にする
2. `maxReadPoints=0` を「無制限（全点読取）」の意味にする
3. 既定値を `maxPoints=0` / `maxReadPoints=0` に変更する
4. 単一巨大バッファではなく、チャンク分割した `THREE.Points` 群へ逐次格納する
5. `rendered` は「実際に描画へ格納した点数」を示し、全点時は `seen == rendered` を保証する

## Consequences

### Positive

- 既定設定で全点描画が可能になる
- 入力点数が多い場合でも、チャンク分割により単一巨大配列の失敗リスクを下げられる

### Negative

- 全点描画はメモリと描画負荷が高く、マシン性能に依存する
- チャンク数が増えるほど描画オブジェクト数も増える

## Completion Criteria

以下をすべて満たしたら完了とする。

1. `examples/sample_las_top_view.html` の既定パラメータが `maxPoints=0` と `maxReadPoints=0` である
2. `maxPoints=0` 時に reservoir sampling を行わず、読み取った各点を描画バッファへ追加する
3. `maxReadPoints=0` 時に EOF まで読み取りを継続する
4. 完了時ステータスで `rendered` が `seen` と一致する（全点モード）
5. 既存要件（`custom_base_plane` 表示、Top View）が維持される
6. `npm run build` が成功する

## Verification Plan

- `npm run build` が成功すること
- `sample_las_top_view.html` の実装で以下を確認すること
  - `maxPoints`/`maxReadPoints` の既定値
  - 全点モードの分岐
  - ステータス出力の `seen` / `rendered`
- 実行時に `Completed` 表示で `seen == rendered` を確認すること（`maxPoints=0&maxReadPoints=0`）
