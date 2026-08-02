# Arkheopantheochive Scene Editor

## Ruling

God Bird Forge is being replaced as the primary authoring surface by the Arkheopantheochive Scene Editor.

The editor is not a random bird generator. It is a deterministic scene-authoring client over a reusable scene model.

## Phase A — Scene Core

This phase provides:

- a deterministic scene graph;
- transform, layer, visibility, and property contracts;
- canonical JSON serialization;
- SHA-256 scene receipts;
- duplicate-ID and malformed-property rejection;
- a complete visual archetype catalog for the Aviary council.

## Scene structure

```text
Scene
├── dimensions
├── background
├── metadata
└── nodes[]
    ├── node_id
    ├── kind
    ├── transform
    ├── layer
    ├── visible
    └── props
```

Node kinds will include `bird`, `terrain`, `light`, `camera`, `text`, `sigil`, `particle_emitter`, and `audio_source`.

## Real rendering pipeline

The browser renderer will consume the exact scene JSON produced by the core:

```text
Scene JSON
→ validation
→ ordered render list
→ camera transform
→ geometry generation
→ material/shader evaluation
→ Canvas2D or WebGL backend
→ frame output
```

The first renderer backend will be Canvas2D because it runs in Termux-hosted Android Chrome without a build step. WebGL becomes a replaceable backend, not a rewrite.

## More birds

The visual catalog includes Duck, Goose, Raven, Gobble, Pheasant, Brother Ape, Owl, Penguin, Eagle, Parrot, Swan, Rooster, Bat, Hummingbird, Dodo, and Paracletheon.

These are visual scene archetypes. Council reasoning plugins remain separate and must continue implementing the Bird contract.

## Verification

```bash
python -m unittest tests.test_scene -v
python verify.py
```

## Failure case

A scene with duplicate node IDs, zero scale, invalid dimensions, or non-JSON properties is rejected before rendering.

## Known limitations

- No renderer backend is included in Phase A.
- No undo/redo command stack yet.
- No asset import or export yet.
- Bird visual geometry is catalogued but not yet implemented.
- Scene receipts prove content integrity, not visual equivalence across browser engines.
