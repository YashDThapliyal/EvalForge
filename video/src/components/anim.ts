import { interpolate, spring, Easing } from "remotion";
import { FPS } from "../theme";

// Fade + rise reveal. `delay` in frames, relative to the current Sequence.
export const reveal = (frame: number, delay = 0, dur = 18) => {
  const p = interpolate(frame, [delay, delay + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return { opacity: p, transform: `translateY(${(1 - p) * 18}px)` };
};

// Simple clamped fade between two frames.
export const fade = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

// Fade edges of a scene: in over first `edge` frames, out over last `edge`.
export const sceneOpacity = (frame: number, duration: number, edge = 14) =>
  interpolate(
    frame,
    [0, edge, duration - edge, duration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

// Springy pop-in for emphasis (stamps, badges).
export const pop = (frame: number, delay = 0, fps = FPS) =>
  spring({ frame: frame - delay, fps, config: { damping: 12, mass: 0.6 } });

// Count a number up from 0 to `value`.
export const countUp = (frame: number, delay: number, dur: number, value: number) =>
  interpolate(frame, [delay, delay + dur], [0, value], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
