import { Frame, Eyebrow, Display, Italic, Body, PrimaryBtn, BackBtn, useDelay } from "../primitives";
import { lime, accent } from "../theme";

interface Props {
  onFinish: () => void;
  onBack?: () => void;
}

export function ScreenDone({ onFinish, onBack }: Props) {
  const s = useDelay(200);

  return (
    <Frame>
      {onBack && <BackBtn onClick={onBack} />}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", position: "relative" }}>
        {[...Array(14)].map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${(i * 47) % 100}%`,
              top: `${(i * 31) % 80}%`,
              width: 6 + (i % 3) * 3,
              height: 6 + (i % 3) * 3,
              background: [lime, accent, "#FF7A45", "#10B981"][i % 4],
              borderRadius: i % 2 === 0 ? "50%" : "2px",
              opacity: s ? 0.85 : 0,
              transform: s ? `translateY(0) rotate(${i * 45}deg)` : "translateY(-20px) rotate(0)",
              transition: `all 1.1s cubic-bezier(.2,.7,.2,1) ${i * 0.04}s`,
            }}
          />
        ))}
        <Eyebrow>todo listo</Eyebrow>
        <Display>
          Estás <Italic>listo</Italic>.
        </Display>
        <div style={{ marginTop: 14 }}>
          <Body>Tu cuenta está configurada. Empezá a registrar gastos y mirá cómo se ordena tu plata.</Body>
        </div>
      </div>
      <PrimaryBtn onClick={onFinish}>Entrar a la app →</PrimaryBtn>
    </Frame>
  );
}
