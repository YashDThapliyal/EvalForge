import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { reveal, pop, sceneOpacity } from "../components/anim";

export const S8CTA: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const logo = pop(frame, 6);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        opacity: sceneOpacity(frame, durationInFrames),
        fontFamily: theme.fontSans,
        color: theme.text,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 34,
      }}
    >
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(120% 90% at 50% 45%, rgba(84,182,247,0.12), rgba(0,0,0,0) 55%)",
        }}
      />
      <div style={{ transform: `scale(${logo})`, opacity: logo, fontSize: 96, fontWeight: 800, letterSpacing: -2 }}>
        Eval<span style={{ color: theme.brand }}>Forge</span>
      </div>

      <div style={{ ...reveal(frame, 34), fontSize: 40, textAlign: "center", maxWidth: 1280, lineHeight: 1.35 }}>
        Most evals end when a model fails a test.
        <br />
        <span style={{ color: theme.brand, fontWeight: 700 }}>
          EvalForge uses that failure to build the next one.
        </span>
      </div>

      <div
        style={{
          ...reveal(frame, 70),
          marginTop: 18,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          border: `1px solid ${theme.brandLine}`,
          borderRadius: 12,
          padding: "18px 34px",
          background: theme.brandFill,
        }}
      >
        <div style={{ fontFamily: theme.fontMono, fontSize: 32, fontWeight: 700, color: theme.brandBright }}>
          github.com/YashDThapliyal/EvalForge
        </div>
        <div style={{ fontSize: 20, color: theme.textDim, letterSpacing: 0.5 }}>
          code · scenarios · fully audited results
        </div>
      </div>
    </AbsoluteFill>
  );
};
