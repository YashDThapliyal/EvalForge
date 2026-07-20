import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { reveal } from "./anim";
import { MODELS } from "../data";

const COLS = { name: 2.4, task: 1, verified: 1, sig: 1.2 };

const Cell: React.FC<{
  flex: number;
  align?: "left" | "right";
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ flex, align = "right", children, style }) => (
  <div style={{ flex, textAlign: align, ...style }}>{children}</div>
);

// Clean six-model table. Single-accent header, soft semantic wash on the two
// rows that carry the story (the win and the reliability gap).
export const ResultsTable: React.FC<{ delay?: number; rowStagger?: number }> = ({
  delay = 0,
  rowStagger = 8,
}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ width: "100%" }}>
      {/* header */}
      <div
        style={{
          ...reveal(frame, delay),
          display: "flex",
          gap: 24,
          padding: "0 26px 16px",
          fontSize: 24,
          fontWeight: 700,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: theme.textFaint,
        }}
      >
        <Cell flex={COLS.name} align="left">Model</Cell>
        <Cell flex={COLS.task}>Task done</Cell>
        <Cell flex={COLS.verified}>Verified</Cell>
        <Cell flex={COLS.sig}>Weaknesses found</Cell>
      </div>

      {MODELS.map((m, i) => {
        const d = delay + 10 + i * rowStagger;
        const isWin = m.highlight === "win";
        const isGap = m.highlight === "gap";
        const tone = isWin ? "pass" : isGap ? "fail" : null;
        const wash = tone ? theme[`${tone}Fill` as const] : "transparent";
        const edge = tone ? theme[tone] : "transparent";
        const vColor = isWin ? theme.pass : isGap ? theme.fail : theme.text;
        return (
          <div
            key={m.name}
            style={{
              ...reveal(frame, d),
              display: "flex",
              gap: 24,
              alignItems: "center",
              padding: "18px 26px",
              background: wash,
              borderLeft: `3px solid ${edge}`,
              borderBottom: `1px solid ${theme.hairline}`,
              borderTopLeftRadius: 8,
              borderBottomLeftRadius: 8,
            }}
          >
            <Cell flex={COLS.name} align="left" style={{ fontSize: 31, fontWeight: 700 }}>
              {m.name}
            </Cell>
            <Cell flex={COLS.task} style={{ fontSize: 30, color: theme.textDim }}>
              {m.task}%
            </Cell>
            <Cell
              flex={COLS.verified}
              style={{ fontSize: 32, fontWeight: 800, color: vColor }}
            >
              {m.verified}%
            </Cell>
            <Cell flex={COLS.sig} style={{ fontSize: 30, color: theme.textDim }}>
              {m.signatures}
            </Cell>
          </div>
        );
      })}
    </div>
  );
};
