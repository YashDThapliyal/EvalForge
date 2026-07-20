import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Caption, Hi } from "../components/Caption";
import { pop, reveal, sceneOpacity } from "../components/anim";

export const S1Problem: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const stamp = pop(frame, 108);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        opacity: sceneOpacity(frame, durationInFrames),
        fontFamily: theme.fontSans,
        color: theme.text,
        padding: "78px 104px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 44,
      }}
    >
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(120% 90% at 50% 8%, rgba(84,182,247,0.10), rgba(0,0,0,0) 55%)",
        }}
      />

      {/* stakes — no context assumed */}
      <div style={{ ...reveal(frame, 4), fontSize: 28, color: theme.textDim, letterSpacing: 1 }}>
        An AI agent is operating your production systems.
      </div>

      {/* the request */}
      <div
        style={{
          ...reveal(frame, 26),
          fontSize: 30,
          fontFamily: theme.fontMono,
          color: theme.brandBright,
          background: theme.surface,
          border: `1px solid ${theme.brandLine}`,
          borderRadius: 12,
          padding: "16px 28px",
        }}
      >
        you: “roll back payments-api to v3”
      </div>

      <div style={{ position: "relative", marginTop: 6 }}>
        {/* agent's confident claim */}
        <div
          style={{
            ...reveal(frame, 58),
            background: theme.surface,
            border: `1px solid ${theme.hairlineBright}`,
            borderRadius: "22px 22px 22px 5px",
            padding: "32px 44px",
            fontSize: 46,
            fontWeight: 600,
            maxWidth: 940,
          }}
        >
          <span style={{ color: theme.pass, marginRight: 14 }}>✓</span>
          “The service was successfully rolled back.”
          <div style={{ fontSize: 23, color: theme.textFaint, marginTop: 12, fontWeight: 500 }}>
            — the agent, reporting its work
          </div>
        </div>

        {/* the stamp of doubt — the motif */}
        <div
          style={{
            position: "absolute",
            right: -66,
            bottom: -60,
            transform: `scale(${stamp}) rotate(-8deg)`,
            opacity: stamp,
            border: `5px solid ${theme.fail}`,
            color: theme.fail,
            fontSize: 56,
            fontWeight: 900,
            letterSpacing: 2,
            padding: "10px 26px",
            borderRadius: 12,
            background: "rgba(10,14,22,0.82)",
          }}
        >
          BUT DID IT?
        </div>
      </div>

      <div style={{ marginTop: 78 }}>
        <Caption delay={150} size={38} maxWidth={1250}>
          Tool-using agents don't just give wrong answers — they fail{" "}
          <Hi tone="fail">while acting</Hi>, then report success.
        </Caption>
      </div>
    </AbsoluteFill>
  );
};
