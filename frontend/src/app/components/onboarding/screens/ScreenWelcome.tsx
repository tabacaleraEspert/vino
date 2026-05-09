import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn, useDelay } from "../primitives";
import { ink } from "../theme";

interface Props {
  onNext: () => void;
  name?: string;
}

export function ScreenWelcome({ onNext, name = "amig@" }: Props) {
  const s1 = useDelay(150);
  const s2 = useDelay(550);
  const s3 = useDelay(900);

  return (
    <Frame>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Eyebrow>Bienvenida</Eyebrow>
        <Display>
          <span style={{ opacity: s1 ? 1 : 0, transition: "opacity .6s" }}>Hola, </span>
          <Italic>
            <span
              style={{
                display: "inline-block",
                opacity: s2 ? 1 : 0,
                transform: s2 ? "translateY(0)" : "translateY(12px)",
                transition: "all .6s cubic-bezier(.2,.7,.2,1)",
              }}
            >
              {name}
            </span>
          </Italic>
          .
        </Display>
        <div
          style={{
            marginTop: 16,
            opacity: s3 ? 1 : 0,
            transform: s3 ? "translateY(0)" : "translateY(12px)",
            transition: "all .6s cubic-bezier(.2,.7,.2,1)",
          }}
        >
          <Body>
            Configuremos tu cuenta en menos de{" "}
            <strong style={{ color: ink }}>2 minutos</strong>. Después, vas a ver dónde se va tu
            plata cada mes.
          </Body>
        </div>
      </div>
      <div
        style={{
          opacity: s3 ? 1 : 0,
          transform: s3 ? "translateY(0)" : "translateY(12px)",
          transition: "all .6s .2s cubic-bezier(.2,.7,.2,1)",
        }}
      >
        <PrimaryBtn onClick={onNext}>Empezar →</PrimaryBtn>
      </div>
    </Frame>
  );
}
