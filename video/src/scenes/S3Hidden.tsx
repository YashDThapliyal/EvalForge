import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Slide, Takeaway, Hi } from "../components/Slide";
import { AnnotatedBlock, Mono } from "../components/AnnotatedBlock";
import { reveal, pop } from "../components/anim";

export const S3Hidden: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const faultP = pop(frame, 196);
  return (
    <Slide
      index={3}
      durationInFrames={durationInFrames}
      title={
        <>
          EvalForge runs the task inside an environment it <Hi>secretly controls</Hi>.
        </>
      }
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 64,
          position: "relative",
        }}
      >
        <AnnotatedBlock label="What the agent sees" tone="brand" delay={22} width={620}>
          <Mono size={25} dim>the task</Mono>
          <Mono size={30}>roll back payments-api → v3</Mono>
          <div style={{ height: 20 }} />
          <Mono size={25} dim>the agent acts</Mono>
          <Mono size={28} color={theme.brandBright}>rollback("payments-api", "v3")</Mono>
          <div style={{ ...reveal(frame, 78), marginTop: 12 }}>
            <Mono size={30} color={theme.pass}>→ SUCCESS ✓</Mono>
          </div>
        </AnnotatedBlock>

        <div style={{ ...reveal(frame, 120), fontSize: 30, color: theme.textFaint, textAlign: "center", width: 60 }}>
          vs
        </div>

        <AnnotatedBlock
          label="The true state — hidden from the agent"
          tone="fail"
          delay={130}
          width={620}
        >
          <Mono size={25} dim>actual service version</Mono>
          <Mono size={30} color={theme.fail}>payments-api = v4  (unchanged)</Mono>
          <div style={{ height: 20 }} />
          <Mono size={25} dim>deploy log</Mono>
          <Mono size={30} color={theme.fail}>empty — nothing was rolled back</Mono>
        </AnnotatedBlock>

        <div
          style={{
            position: "absolute",
            bottom: -12,
            left: "50%",
            transform: `translateX(-50%) scale(${faultP})`,
            opacity: faultP,
            background: theme.bg,
            border: `1px solid ${theme.failLine}`,
            color: theme.fail,
            fontSize: 25,
            fontWeight: 700,
            padding: "10px 24px",
            borderRadius: 40,
            fontFamily: theme.fontMono,
          }}
        >
          injected fault — the tool reported success but changed nothing
        </div>
      </div>

      <Takeaway delay={236}>
        Same story the agent told — but EvalForge can see the rollback{" "}
        <Hi tone="fail">never happened</Hi>.
      </Takeaway>
    </Slide>
  );
};
