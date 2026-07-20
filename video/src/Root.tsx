import React from "react";
import { AbsoluteFill, Composition, Series } from "remotion";
import { FPS, WIDTH, HEIGHT, theme } from "./theme";
import { S1Problem } from "./scenes/S1Problem";
import { S2WhyMiss } from "./scenes/S2WhyMiss";
import { S3Hidden } from "./scenes/S3Hidden";
import { S4Verdict } from "./scenes/S4Verdict";
import { S5Sources } from "./scenes/S5Sources";
import { S6FailureDirected } from "./scenes/S6FailureDirected";
import { S7Results } from "./scenes/S7Results";
import { S8CTA } from "./scenes/S8CTA";

// Scene durations in frames @ 30fps. One example threads through all of them.
const D = {
  s1: 300, // 10s — the problem (cold open, "but did it?")
  s2: 240, // 8s  — why evals miss it
  s3: 360, // 12s — the hidden environment
  s4: 390, // 13s — the verdict (five checks, explained)
  s5: 210, // 7s  — the three-stage gauntlet
  s6: 330, // 11s — doubling down on failure (failure-directed)
  s7: 330, // 11s — the results
  s8: 150, // 5s  — CTA
};

export const TOTAL =
  D.s1 + D.s2 + D.s3 + D.s4 + D.s5 + D.s6 + D.s7 + D.s8; // 2310 = 77s

// Persistent author credit, bottom-left on every scene.
const Watermark: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div
      style={{
        position: "absolute",
        left: 104,
        bottom: 44,
        display: "flex",
        alignItems: "center",
        gap: 9,
        fontFamily: theme.fontSans,
        fontSize: 19,
        fontWeight: 600,
        letterSpacing: 0.4,
        color: theme.textFaint,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: theme.brand, opacity: 0.85 }} />
      Yash D Thapliyal
    </div>
  </AbsoluteFill>
);

const EvalForgeDemo: React.FC = () => (
  <AbsoluteFill>
    <Series>
    <Series.Sequence durationInFrames={D.s1}>
      <S1Problem durationInFrames={D.s1} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s2}>
      <S2WhyMiss durationInFrames={D.s2} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s3}>
      <S3Hidden durationInFrames={D.s3} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s4}>
      <S4Verdict durationInFrames={D.s4} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s5}>
      <S5Sources durationInFrames={D.s5} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s6}>
      <S6FailureDirected durationInFrames={D.s6} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s7}>
      <S7Results durationInFrames={D.s7} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={D.s8}>
      <S8CTA durationInFrames={D.s8} />
    </Series.Sequence>
    </Series>
    <Watermark />
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EvalForgeDemo"
    component={EvalForgeDemo}
    durationInFrames={TOTAL}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
