import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Slide, Takeaway, Hi } from "../components/Slide";
import { SIGNATURE, CHILDREN } from "../data";
import { reveal, pop } from "../components/anim";

export const S6FailureDirected: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  return (
    <Slide
      index={6}
      durationInFrames={durationInFrames}
      titleSize={46}
      title={
        <>
          Catch a failure → <Hi>generate more tests just like it</Hi>.
        </>
      }
    >
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 48 }}>
        {/* left: the caught failure + its signature */}
        <div style={{ width: 540, flexShrink: 0, display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              ...reveal(frame, 20),
              background: theme.failFill,
              border: `1px solid ${theme.failLine}`,
              borderRadius: 14,
              padding: "22px 26px",
            }}
          >
            <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: 1.4, textTransform: "uppercase", color: theme.fail }}>
              ✕ Caught failure
            </div>
            <div style={{ fontSize: 27, marginTop: 8, lineHeight: 1.35 }}>
              the agent claimed a rollback that never happened
            </div>
          </div>

          <div style={{ ...reveal(frame, 58), fontSize: 30, color: theme.textFaint, textAlign: "center" }}>
            ↓ extract a stable signature
          </div>

          <div
            style={{
              ...reveal(frame, 70),
              background: theme.brandFill,
              border: `1px solid ${theme.brandLine}`,
              borderRadius: 14,
              padding: "20px 26px",
            }}
          >
            <div style={{ fontFamily: theme.fontMono, fontSize: 26, color: theme.brandBright }}>
              {SIGNATURE}
            </div>
            <div style={{ fontSize: 22, color: theme.textDim, marginTop: 6 }}>
              stable even when names & IDs change
            </div>
          </div>
        </div>

        {/* branch arrow */}
        <div style={{ ...reveal(frame, 104), fontSize: 46, color: theme.brand, flexShrink: 0 }}>→</div>

        {/* right: the targeted children */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              ...reveal(frame, 108),
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              color: theme.brand,
              marginBottom: 14,
            }}
          >
            new synthetic tests, aimed at the same weakness
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {CHILDREN.map((c, i) => (
              <div
                key={c.title}
                style={{
                  ...reveal(frame, 128 + i * 26),
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                  background: theme.surface,
                  border: `1px solid ${theme.brandLine}`,
                  borderLeft: `4px solid ${theme.brand}`,
                  borderRadius: 12,
                  padding: "16px 22px",
                }}
              >
                <span style={{ fontFamily: theme.fontMono, fontSize: 22, color: theme.brand, fontWeight: 700 }}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <div style={{ fontSize: 28, fontWeight: 700 }}>{c.title}</div>
                  <div style={{ fontSize: 22, color: theme.textDim, marginTop: 2 }}>{c.sub}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ ...reveal(frame, 210), fontSize: 23, color: theme.textFaint, marginTop: 14 }}>
            each is validated by an oracle, then re-run against the model ↺
          </div>
        </div>
      </div>

      <Takeaway delay={244}>
        One caught failure becomes a <Hi>family of targeted stress tests</Hi> — EvalForge
        doubles down exactly where the model is weak.
      </Takeaway>
    </Slide>
  );
};
