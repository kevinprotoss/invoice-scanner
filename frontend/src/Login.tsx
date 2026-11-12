import { FormEvent, useState } from "react";
import { login } from "./api";

export default function Login({ onOk }: { onOk: () => void }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const ok = await login(pw);
      if (ok) onOk();
      else setErr("密码错误");
    } catch {
      setErr("无法连接服务器");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <form className="card" onSubmit={submit}>
        <h1>Invoice Scanner</h1>
        <p className="muted">请输入访问密码</p>
        <input
          type="password"
          autoComplete="current-password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="访问密码"
        />
        {err && <div className="error">{err}</div>}
        <button type="submit" disabled={busy || !pw}>
          {busy ? "登录中…" : "登录"}
        </button>
      </form>
    </div>
  );
}