import { useEffect, useState } from "react";
import Login from "./Login";
import InvoiceList from "./pages/InvoiceList";
import Upload from "./pages/Upload";
import InvoiceDetail from "./pages/InvoiceDetail";
import { logout, me } from "./api";

type AuthState = "loading" | "anon" | "auth";
type Route =
  | { name: "list" }
  | { name: "upload" }
  | { name: "detail"; id: string };

function parseHash(): Route {
  const h = window.location.hash.replace(/^#/, "");
  if (h === "/upload") return { name: "upload" };
  const m = h.match(/^\/invoice\/(.+)$/);
  if (m) return { name: "detail", id: decodeURIComponent(m[1]) };
  return { name: "list" };
}

export default function App() {
  const [state, setState] = useState<AuthState>("loading");
  const [route, setRoute] = useState<Route>(parseHash());

  useEffect(() => {
    me()
      .then((ok) => setState(ok ? "auth" : "anon"))
      .catch(() => setState("anon"));
  }, []);

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (state === "loading") return <div className="center muted">加载中…</div>;
  if (state === "anon") return <Login onOk={() => setState("auth")} />;

  async function doLogout() {
    await logout();
    setState("anon");
  }

  return (
    <div className="page">
      <header className="topbar">
        <a href="#/" className="brand">Invoice Scanner</a>
        <button className="link" onClick={doLogout}>退出</button>
      </header>
      <main className="content">
        {route.name === "list" && <InvoiceList />}
        {route.name === "upload" && (
          <Upload
            onDone={(id) => {
              window.location.hash = `#/invoice/${id}`;
            }}
          />
        )}
        {route.name === "detail" && <InvoiceDetail id={route.id} />}
      </main>
    </div>
  );
}