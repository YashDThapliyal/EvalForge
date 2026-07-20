// Central design tokens for the EvalForge explainer.
// ONE brand accent (sky). Green/red used ONLY for pass/fail semantics.
// No competing third/fourth hues — cohesion over decoration.

export const theme = {
  // neutrals — deep ink, layered slate surfaces
  bg: "#0A0E16",
  bgDeep: "#070A11",
  surface: "#121826",
  surfaceAlt: "#19212F",
  hairline: "#232C3C",
  hairlineBright: "#33405A",

  text: "#EDF1F8",
  textDim: "#95A2B6",
  textFaint: "#5B6A7C",

  // single brand accent
  brand: "#54B6F7",
  brandBright: "#8CD0FF",
  brandFill: "rgba(84,182,247,0.12)",
  brandLine: "rgba(84,182,247,0.35)",

  // semantics — reserved strictly for verified/failure meaning
  pass: "#43D6A0",
  passFill: "rgba(67,214,160,0.12)",
  passLine: "rgba(67,214,160,0.40)",
  fail: "#FB6E7E",
  failFill: "rgba(251,110,126,0.12)",
  failLine: "rgba(251,110,126,0.42)",

  fontSans:
    '"Inter", -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
  fontMono:
    '"SF Mono", "JetBrains Mono", "Fira Code", ui-monospace, Menlo, monospace',
} as const;

// The narrative spine — one section per content slide (CTA excluded).
export const SECTIONS = [
  "The problem",
  "Why evals miss it",
  "The hidden world",
  "The verdict",
  "Where tests come from",
  "Doubling down on failure",
  "The results",
];

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
