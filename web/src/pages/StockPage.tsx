import { useParams } from "react-router-dom";

export function StockPage() {
  const { symbol = "PLTR" } = useParams();
  return <section><p className="eyebrow">Research asset</p><h1>{symbol}</h1><p className="lede">Live report routing is ready. The evidence view will be populated by the QuantMind API.</p><a className="cta" href={`/api/report/${symbol}`}>Open API report →</a></section>;
}
