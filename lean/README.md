# Lean

The map's Lean layer is one lake package, [`bridge/`](bridge/README.md), pinned to one Physlib revision and one Lean toolchain. It declares each node's dimension as a Physlib seven-base ISQ `Dimension` and holds the compiled formula bridges. Build it from `lean/bridge` with `lake exe cache get` and `lake build --wfail`.

An earlier package in this directory, on a separate Physlib pin and Lean 4.31.0, was retired on 2026-10-28. It held five-base node dimensions, 13 edge-dimension equalities and 18 theorems that restated closed-form formulas (from `Y = N/D` conclude `Y*D = N`). None of these certified anything about the physics, and the bridge already declares every node's dimension at the current pin. The files remain in the git history.
