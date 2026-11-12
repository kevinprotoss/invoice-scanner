import { useEffect, useState } from "react";
import { logout } from "./api";

export default function Home({ onLogout }: { onLogout: () => void }) {
  const [installEvent, setInstallEvent] = useState<any>(null);
  const [installed, setInstalled] = useState(false);
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as any).standalone === true;

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e);
    };
    window.addEventListener("beforeinstallprompt", handler);
    window.addEventListener("appinstalled", () => setInstalled(true));
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  async function doLogout() {
    await logout();
    onLogout();
  }

  return (
    <div className="page">
      <header className="topbar">
        <strong>Invoice Scanner</strong>
        <button className="link" onClick={doLogout}>
          退出
        </button>
      </header>

      <main className="content">
        <section className="card">
          <h2>Phase 1 已就绪</h2>
          <p>HTTPS、访问密码、PWA 外壳已部署。上传与账单功能将在后续阶段加入。</p>
          <ul>
            <li>运行模式：{isStandalone ? "standalone（已安装）" : "浏览器"}</li>
            <li>设备：{isIOS ? "iOS / iPadOS" : "其他"}</li>
          </ul>
        </section>

        {!isStandalone && (
          <section className="card">
            <h2>安装到主屏幕</h2>
            {installEvent && !installed && (
              <button
                onClick={async () => {
                  installEvent.prompt();
                  const choice = await installEvent.userChoice;
                  if (choice.outcome === "accepted") setInstalled(true);
                  setInstallEvent(null);
                }}
              >
                安装应用
              </button>
            )}
            {isIOS && (
              <p className="muted">
                iPhone / iPad：用 Safari 打开本页 → 分享 → 添加到主屏幕。
              </p>
            )}
            {!isIOS && !installEvent && (
              <p className="muted">
                Android Chrome：浏览器菜单 → 安装应用 / 添加到主屏幕。
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}