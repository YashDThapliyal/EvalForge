import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { reveal } from "./anim";

// Narration line for the full-bleed open/close scenes.
export const Caption: React.FC<{
  delay?: number;
  size?: number;
  maxWidth?: number;
  children: React.ReactNode;
  tone?: "text" | "dim" | "brand";
}> = ({ delay = 0, size = 40, maxWidth = 1300, children, tone = "text" }) => {
  const frame = useCurrentFrame();
  const color = tone === "dim" ? theme.textDim : tone === "brand" ? theme.brand : theme.text;
  return (
    <div
      style={{
        ...reveal(frame, delay),
        fontSize: size,
        lineHeight: 1.35,
        fontWeight: 500,
        color,
        textAlign: "center",
        maxWidth,
        marginLeft: "auto",
        marginRight: "auto",
      }}
    >
      {children}
    </div>
  );
};

export const Hi: React.FC<{ tone?: "brand" | "pass" | "fail"; children: React.ReactNode }> = ({
  tone = "brand",
  children,
}) => <span style={{ color: theme[tone], fontWeight: 800 }}>{children}</span>;
