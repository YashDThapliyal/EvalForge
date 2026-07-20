import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Slide, Takeaway, Hi } from "../components/Slide";
import { reveal, pop } from "../components/anim";

export const S2WhyMiss: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const passStamp = pop(frame, 120);
  return (
    <Slide
      index={2}
      durationInFrames={durationInFrames}
      title={
        <>
          A normal benchmark only reads the agent's <Hi>answer</Hi>.
        </>
      }
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 40,
        }}
      >
        {/* the words */}
        <div
          style={{
            ...reveal(frame, 24),
            background: theme.surface,
            border: `1px solid ${theme.hairlineBright}`,
            borderRadius: 14,
            padding: "26px 32px",
            fontSize: 34,
            fontFamily: theme.fontMono,
            color: theme.text,
            maxWidth: 560,
          }}
        >
          <span style={{ color: theme.pass }}>✓</span> “rolled back”
        </div>

        <div style={{ ...reveal(frame, 60), fontSize: 40, color: theme.textFaint }}>→</div>

        {/* the judge */}
        <div
          style={{
            ...reveal(frame, 76),
            border: `1px dashed ${theme.hairlineBright}`,
            borderRadius: 14,
            padding: "26px 34px",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 24, color: theme.textDim, letterSpacing: 1 }}>
            response-only eval / LLM judge
          </div>
          <div style={{ fontSize: 26, color: theme.textFaint, marginTop: 8 }}>
            sees only these words
          </div>
        </div>

        <div style={{ ...reveal(frame, 108), fontSize: 40, color: theme.textFaint }}>→</div>

        {/* wrong verdict */}
        <div
          style={{
            transform: `scale(${passStamp})`,
            opacity: passStamp,
            border: `3px solid ${theme.pass}`,
            color: theme.pass,
            borderRadius: 12,
            padding: "18px 30px",
            fontSize: 44,
            fontWeight: 900,
            letterSpacing: 2,
            position: "relative",
          }}
        >
          PASS
          <div
            style={{
              position: "absolute",
              bottom: -34,
              left: 0,
              right: 0,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 1,
              color: theme.fail,
            }}
          >
            …but it's wrong
          </div>
        </div>
      </div>

      <Takeaway delay={150}>
        The judge sees the same story the agent tells. It <Hi tone="fail">can't check</Hi>{" "}
        what actually happened when the agent acted.
      </Takeaway>
    </Slide>
  );
};
