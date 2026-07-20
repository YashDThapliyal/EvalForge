import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Slide, Hi } from "../components/Slide";
import { ResultsTable } from "../components/ResultsTable";
import { RUN_SCOPE } from "../data";
import { reveal } from "../components/anim";

const Read: React.FC<{ frame: number; delay: number; tone: "pass" | "fail"; children: React.ReactNode }> = ({
  frame,
  delay,
  tone,
  children,
}) => (
  <div
    style={{
      ...reveal(frame, delay),
      display: "flex",
      gap: 14,
      alignItems: "flex-start",
      fontSize: 28,
      lineHeight: 1.4,
    }}
  >
    <span style={{ color: theme[tone], fontSize: 26, marginTop: 3 }}>●</span>
    <span>{children}</span>
  </div>
);

export const S7Results: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  return (
    <Slide
      index={7}
      durationInFrames={durationInFrames}
      titleSize={46}
      title={
        <>
          Six live models. <Hi>“Verified”</Hi> = did it actually work?
        </>
      }
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <ResultsTable delay={16} />

        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 26 }}>
          <Read frame={frame} delay={150} tone="pass">
            <b>GPT-5.6 Sol — 91.7%:</b> task done <b>and</b> every claim verified against real
            state.
          </Read>
          <Read frame={frame} delay={182} tone="fail">
            <b>Claude Sonnet 5 — 58.3% task, 44.4% verified:</b> a 14-point gap. “Task done”{" "}
            <Hi tone="fail">overstated</Hi> reliability — the “but did it?” gap, quantified.
          </Read>
        </div>

        <div
          style={{
            ...reveal(frame, 220),
            marginTop: 22,
            fontSize: 22,
            color: theme.textFaint,
            fontFamily: theme.fontMono,
          }}
        >
          {RUN_SCOPE.episodes} episodes · {RUN_SCOPE.models} models · seed {RUN_SCOPE.seed} ·
          {" "}fully audited &amp; reproducible
        </div>
      </div>
    </Slide>
  );
};
