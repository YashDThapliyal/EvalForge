import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { pop, reveal } from "./anim";
import { VERIFIER_CHECKS } from "../data";

// The five verifier dimensions. Each row teaches the term (plain-English
// question) and then shows the result for the rollback example.
export const VerifierChecklist: React.FC<{ delay?: number; stagger?: number }> = ({
  delay = 0,
  stagger = 16,
}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
      {VERIFIER_CHECKS.map((c, i) => {
        const d = delay + i * stagger;
        const markP = pop(frame, d + 5);
        const color = c.pass ? theme.pass : theme.fail;
        const fill = c.pass ? theme.passFill : theme.failFill;
        const line = c.pass ? theme.passLine : theme.failLine;
        return (
          <div
            key={c.label}
            style={{
              ...reveal(frame, d),
              display: "flex",
              alignItems: "center",
              gap: 22,
              background: fill,
              border: `1px solid ${line}`,
              borderRadius: 12,
              padding: "15px 24px",
            }}
          >
            <span
              style={{
                transform: `scale(${markP})`,
                fontSize: 30,
                fontWeight: 900,
                color,
                width: 34,
                textAlign: "center",
                flexShrink: 0,
              }}
            >
              {c.pass ? "✓" : "✕"}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
                <span style={{ fontSize: 28, fontWeight: 800, width: 245, flexShrink: 0 }}>
                  {c.label}
                </span>
                <span style={{ fontSize: 24, color: theme.textDim }}>{c.means}</span>
              </div>
              <div style={{ fontSize: 23, fontWeight: 700, color, marginTop: 4, marginLeft: 259 }}>
                {c.note}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
