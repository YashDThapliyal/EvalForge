import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Slide, Takeaway, Hi } from "../components/Slide";
import { SOURCES } from "../data";
import { reveal, pop } from "../components/anim";

// A short verb per stage so the sequence reads as a pipeline, not a menu.
const STEP_VERB = ["start with the fixed set", "then widen the net", "then aim at the cracks"];

// The connector between two stages. The one feeding the adaptive stage carries
// a "weakness shows up" trigger — that's what flips EvalForge from broad to targeted.
const Connector: React.FC<{
  frame: number;
  delay: number;
  highlight: boolean;
  trigger: number;
}> = ({ frame, delay, highlight, trigger }) => (
  <div
    style={{
      width: highlight ? 170 : 74,
      flexShrink: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      position: "relative",
    }}
  >
    {highlight && (
      <div
        style={{
          transform: `scale(${trigger})`,
          opacity: trigger,
          position: "absolute",
          top: 34,
          width: 170,
          textAlign: "center",
          fontSize: 18,
          fontWeight: 800,
          letterSpacing: 0.4,
          lineHeight: 1.25,
          color: theme.fail,
        }}
      >
        ✕ a weakness
        <br />
        shows up
      </div>
    )}
    <div
      style={{
        ...reveal(frame, delay),
        fontSize: 42,
        color: highlight ? theme.brand : theme.textFaint,
      }}
    >
      →
    </div>
  </div>
);

export const S5Sources: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const trigger = pop(frame, 96);
  return (
    <Slide
      index={5}
      durationInFrames={durationInFrames}
      titleSize={46}
      title={
        <>
          Every model runs the same gauntlet — in <Hi>three stages</Hi>.
        </>
      }
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{ display: "flex", alignItems: "center" }}>
          {SOURCES.map((s, i) => {
            const isFailure = s.key === "failure";
            const accent = isFailure ? theme.brand : theme.hairlineBright;
            return (
              <React.Fragment key={s.key}>
                {i > 0 && (
                  <Connector
                    frame={frame}
                    delay={42 + (i - 1) * 48}
                    highlight={isFailure}
                    trigger={isFailure ? trigger : 0}
                  />
                )}
                <div
                  style={{
                    ...reveal(frame, 22 + i * 48),
                    flex: 1,
                    background: isFailure ? theme.brandFill : theme.surface,
                    border: `1px solid ${isFailure ? theme.brandLine : theme.hairline}`,
                    borderTop: `4px solid ${accent}`,
                    borderRadius: 14,
                    padding: "26px 28px",
                    minHeight: 252,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span
                      style={{
                        fontFamily: theme.fontMono,
                        fontSize: 21,
                        fontWeight: 700,
                        letterSpacing: 1,
                        color: isFailure ? theme.brand : theme.textFaint,
                      }}
                    >
                      STAGE {s.n}
                    </span>
                    <span
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        letterSpacing: 1,
                        textTransform: "uppercase",
                        color: isFailure ? theme.brand : theme.textFaint,
                      }}
                    >
                      {s.tag}
                    </span>
                  </div>
                  <div style={{ fontSize: 20, color: theme.textFaint, marginTop: 16, letterSpacing: 0.3 }}>
                    {STEP_VERB[i]}
                  </div>
                  <div style={{ fontSize: 34, fontWeight: 800, marginTop: 4 }}>{s.title}</div>
                  <div style={{ fontSize: 22, color: theme.textDim, marginTop: 12, lineHeight: 1.4 }}>
                    {s.sub}
                  </div>
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* scope note — honest about what's built today vs. what generalizes */}
        <div
          style={{
            ...reveal(frame, 124),
            marginTop: 34,
            display: "flex",
            alignItems: "baseline",
            gap: 16,
            fontSize: 21,
            color: theme.textFaint,
            lineHeight: 1.4,
          }}
        >
          <span
            style={{
              fontFamily: theme.fontMono,
              fontSize: 16,
              fontWeight: 700,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              color: theme.brand,
              whiteSpace: "nowrap",
            }}
          >
            Scope today
          </span>
          <span>
            one domain —{" "}
            <span style={{ color: theme.textDim, fontWeight: 700 }}>cloud-infra operations</span>. The
            generate → verify loop is domain-agnostic; new domains plug in without changing the engine.
          </span>
        </div>
      </div>

      <Takeaway delay={140}>
        All three are scored by the <Hi>same environment</Hi>. The moment a model slips, EvalForge
        stops casting wide and starts aiming — <Hi>the next stage is bred from that failure</Hi>.
      </Takeaway>
    </Slide>
  );
};
