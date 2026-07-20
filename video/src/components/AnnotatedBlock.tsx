import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { reveal } from "./anim";

// A labeled panel — the "annotated block on screen" the demo is built around.
export const AnnotatedBlock: React.FC<{
  label: string;
  tone?: "brand" | "pass" | "fail";
  delay?: number;
  width?: number | string;
  children: React.ReactNode;
}> = ({ label, tone = "brand", delay = 0, width = 620, children }) => {
  const frame = useCurrentFrame();
  const color = theme[tone];
  const line = theme[`${tone}Line` as const];
  const fill = theme[`${tone}Fill` as const];
  return (
    <div style={{ ...reveal(frame, delay), width, position: "relative" }}>
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 10,
          fontSize: 19,
          fontWeight: 800,
          letterSpacing: 1.6,
          textTransform: "uppercase",
          color,
          marginBottom: 14,
        }}
      >
        <span style={{ width: 9, height: 9, borderRadius: 9, background: color }} />
        {label}
      </div>
      <div
        style={{
          border: `1px solid ${line}`,
          background: `linear-gradient(180deg, ${fill}, rgba(0,0,0,0))`,
          backgroundColor: theme.surface,
          borderRadius: 16,
          padding: "28px 30px",
        }}
      >
        {children}
      </div>
    </div>
  );
};

// A mono "code" line for tool calls / state.
export const Mono: React.FC<{
  color?: string;
  size?: number;
  dim?: boolean;
  children: React.ReactNode;
}> = ({ color, size = 30, dim, children }) => (
  <div
    style={{
      fontFamily: theme.fontMono,
      fontSize: size,
      color: color ?? (dim ? theme.textFaint : theme.text),
      lineHeight: 1.55,
      whiteSpace: "pre-wrap",
    }}
  >
    {children}
  </div>
);
