import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { SearchProvider, useSearch } from "./components/SearchPalette";
import { HomePage } from "./pages/HomePage";
import { MemoryPage } from "./pages/MemoryPage";
import { StockPage } from "./pages/StockPage";
import "./style.css";

function Header() {
  const { openSearch } = useSearch();
  return (
    <header>
      <Link to="/" className="brand">QUANTMIND</Link>
      <nav><Link to="/">Universe</Link><Link to="/memory">Memory</Link></nav>
      <button className="search-button" onClick={openSearch}>Search <kbd>Ctrl K</kbd></button>
    </header>
  );
}

function App() {
  const [searchOpen, setSearchOpen] = useState(false);
  return (
    <SearchProvider open={searchOpen} setOpen={setSearchOpen}>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/stock/:symbol" element={<StockPage />} />
          <Route path="/memory" element={<MemoryPage />} />
        </Routes>
      </main>
    </SearchProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>,
);
