import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { SearchProvider, useSearch } from "./components/SearchPalette";
import { HomePage } from "./pages/HomePage";
import { MemoryPage } from "./pages/MemoryPage";
import { StockPage } from "./pages/StockPage";
import "./style.css";

function Header() {
  const { openSearch } = useSearch();
  return <header className="topbar"><Link to="/" className="brand"><span>QM</span> QUANTMIND</Link><nav><Link to="/">Terminal</Link><Link to="/memory">Memory</Link></nav><button className="search-button" onClick={openSearch}>SEARCH <kbd>CTRL K</kbd></button></header>;
}

function App() {
  return <SearchProvider><Header /><main><Routes><Route path="/" element={<HomePage />} /><Route path="/stock/:symbol" element={<StockPage />} /><Route path="/memory" element={<MemoryPage />} /></Routes></main><footer>QUANTMIND · EVIDENCE-FIRST MARKET RESEARCH · NOT FINANCIAL ADVICE</footer></SearchProvider>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>);
