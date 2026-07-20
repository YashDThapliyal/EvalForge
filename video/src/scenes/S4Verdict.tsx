import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Slide, Takeaway, Hi } from "../components/Slide";
import { VerifierChecklist } from "../components/VerifierChecklist";
import { pop } from "../components/anim";

export const S4Verdict: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const verdict = pop(frame, 200);
  return (
    <Slide
      index={4}
      durationInFrames={durationInFrames}
      titleSize={46}
      title={
        <>
          So it checks the claim against reality — <Hi>five ways</Hi>.
        </>
      }
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 24 }}>
        <VerifierChecklist delay={24} />

        {/* verdict banner */}
        <div
          style={{
            transform: `scale(${0.96 + verdict * 0.04})`,
            opacity: verdict,
            display: "flex",
            alignItems: "center",
            gap: 26,
            background: theme.failFill,
            border: `1px solid ${theme.failLine}`,
            borderRadius: 14,
            padding: "18px 30px",
          }}
        >
          <span style={{ fontSize: 24, letterSpacing: 3, fontWeight: 700, color: theme.textDim }}>
            VERDICT
          </span>
          <span style={{ fontSize: 52, fontWeight: 900, color: theme.fail, letterSpacing: 1 }}>
            FAILED
          </span>
          <span style={{ fontSize: 26, color: theme.textDim, marginLeft: "auto" }}>
            2 of 5 checks failed — the agent's claim did not match reality
          </span>
        </div>
      </div>

      <Takeaway delay={236}>
        <Hi tone="fail">“But did it?”</Hi> — the environment decides the truth, not a judge's
        opinion. <Hi>No LLM in the loop.</Hi>
      </Takeaway>
    </Slide>
  );
};
