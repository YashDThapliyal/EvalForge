import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { theme, SECTIONS } from "../theme";
import { sceneOpacity, reveal } from "./anim";

// The shared scaffold every content slide uses. A consistent step rail +
// progress ticks + title zone is what makes the deck feel like one system.
export const Slide: React.FC<{
  index: number; // 1-based section number
  title: React.ReactNode;
  durationInFrames: number;
  children: React.ReactNode;
  titleSize?: number;
}> = ({ index, title, durationInFrames, children, titleSize = 50 }) => {
  const frame = useCurrentFrame();
  const section = SECTIONS[index - 1];
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
      }}
    >
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(120% 90% at 50% -10%, rgba(84,182,247,0.08), rgba(0,0,0,0) 55%)",
        }}
      />

      {/* step rail */}
      <div
        style={{
          ...reveal(frame, 2),
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 26,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
          <span
            style={{
              fontFamily: theme.fontMono,
              fontSize: 24,
              fontWeight: 700,
              color: theme.brand,
            }}
          >
            {String(index).padStart(2, "0")}
          </span>
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: theme.textDim,
            }}
          >
            {section}
          </span>
        </div>
        <ProgressTicks index={index} />
      </div>

      {/* title */}
      <div
        style={{
          ...reveal(frame, 8),
          fontSize: titleSize,
          fontWeight: 700,
          letterSpacing: -0.5,
          lineHeight: 1.12,
          marginBottom: 40,
          maxWidth: 1500,
        }}
      >
        {title}
      </div>

      {/* content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

const ProgressTicks: React.FC<{ index: number }> = ({ index }) => (
  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
    {SECTIONS.map((_, i) => {
      const active = i + 1 === index;
      const done = i + 1 < index;
      return (
        <div
          key={i}
          style={{
            width: active ? 34 : 12,
            height: 6,
            borderRadius: 3,
            background: active
              ? theme.brand
              : done
              ? theme.hairlineBright
              : theme.hairline,
            transition: "all 0.2s",
          }}
        />
      );
    })}
  </div>
);

// Shared bottom caption — one consistent style across slides.
export const Takeaway: React.FC<{
  delay?: number;
  children: React.ReactNode;
}> = ({ delay = 0, children }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        ...reveal(frame, delay),
        marginTop: 34,
        paddingTop: 26,
        borderTop: `1px solid ${theme.hairline}`,
        fontSize: 32,
        lineHeight: 1.4,
        color: theme.textDim,
        maxWidth: 1500,
      }}
    >
      {children}
    </div>
  );
};

export const Hi: React.FC<{ tone?: "brand" | "pass" | "fail"; children: React.ReactNode }> = ({
  tone = "brand",
  children,
}) => (
  <span style={{ color: theme[tone], fontWeight: 800 }}>{children}</span>
);
