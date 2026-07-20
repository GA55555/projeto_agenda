// Stat tile do dashboard com tooltip explicativo (Fase 7e): passar `info` faz
// aparecer um ⓘ; hover/foco (e toque, via focus) abre um balão dizendo COMO o
// número foi calculado — resumido, coeso e direto.
interface StatProps {
  valor: string | number;
  rotulo: string;
  info?: string;
  alerta?: boolean;
}

export function Stat({ valor, rotulo, info, alerta }: StatProps) {
  return (
    <div className={`stat${alerta ? " alerta" : ""}`}>
      <span className="num">{valor}</span>
      <span className="rot">
        {rotulo}
        {info && (
          <span className="info" tabIndex={0} aria-label={info}>
            ⓘ<span className="tooltip" role="tooltip">{info}</span>
          </span>
        )}
      </span>
    </div>
  );
}
