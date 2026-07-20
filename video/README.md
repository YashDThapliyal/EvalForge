# EvalForge demo video

A ~72-second animated explainer (Remotion) that walks a cold viewer through what
EvalForge is, using one worked example (an **ambiguous rollback**: the tool reports
success but the state never changed), the three scenario sources, the five-dimension
verifier, the failure-directed learn loop, and the audited six-model results.

On-screen text only — no audio track content (a silent track is present by default).
All numbers come from `../results/model-suite/comparison.json` (mirrored in `src/data.ts`).

## Launch

```bash
cd video
npm install          # first time only (Node 18+; Node 22 tested)

# live preview — scrub / edit in the browser
npx remotion studio

# render the MP4 → out/evalforge-demo.mp4
npx remotion render EvalForgeDemo out/evalforge-demo.mp4

# single still for a quick check (frame N)
npx remotion still EvalForgeDemo out/frame.png --frame=720
```

The rendered file is `out/evalforge-demo.mp4` (double-click to play). `out/` and
`node_modules/` are gitignored.

## Structure

- `src/Root.tsx` — composition + scene timeline (durations, 30fps, 1920×1080)
- `src/scenes/` — one file per beat (S1 problem → S8 CTA)
- `src/components/` — reusable pieces (`AnnotatedBlock`, `LoopDiagram`,
  `VerifierChecklist`, `ResultsTable`, captions, animation helpers)
- `src/theme.ts` — design tokens · `src/data.ts` — the real audited numbers

To change a number on screen, edit `src/data.ts` (keep it in sync with the audited
results) and re-render.
