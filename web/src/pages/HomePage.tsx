import { Link } from "react-router-dom";
import { useSearch } from "../components/SearchPalette";

export function HomePage() {
  const { openSearch } = useSearch();
  return <section className="hero"><p className="eyebrow">Evidence before conviction</p><h1>Search the market<br /><em>with memory.</em></h1><p className="lede">A research terminal for live catalysts, deterministic signals, and Hindsight precedent.</p><button className="search-button" onClick={openSearch}>Search the universe</button><Link className="cta" to="/stock/PLTR">Open PLTR research →</Link></section>;
}
