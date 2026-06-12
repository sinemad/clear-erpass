import { useEffect, useState } from "react";
import { fetchConfig, saveConfig, type ConfigRead } from "../../api/config";
import styles from "./SettingsPage.module.css";

type SaveState = "idle" | "saving" | "saved" | "error";

export default function SettingsPage() {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [verifySSL, setVerifySSL] = useState(true);
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    fetchConfig()
      .then((cfg: ConfigRead) => {
        setUrl(cfg.clearpass_base_url ?? "");
        setVerifySSL(cfg.clearpass_verify_ssl);
        setTokenConfigured(cfg.clearpass_api_token_configured);
      })
      .catch(() => {/* server may not be reachable yet */});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaveState("saving");
    setErrorMsg("");
    try {
      const cfg = await saveConfig({
        clearpass_base_url: url,
        clearpass_api_token: token || undefined,
        clearpass_verify_ssl: verifySSL,
      });
      setTokenConfigured(cfg.clearpass_api_token_configured);
      setToken("");
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 3000);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setSaveState("error");
    }
  }

  return (
    <div className={styles.page}>
      <h1>Settings</h1>
      <p className={styles.description}>
        Configure the ClearPass Policy Manager server this app connects to.
      </p>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label htmlFor="url">ClearPass Server URL</label>
          <input
            id="url"
            type="url"
            required
            placeholder="https://clearpass.example.com (or …/api)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="token">
            API Token
            {tokenConfigured && (
              <span className={styles.tokenBadge}>configured</span>
            )}
          </label>
          <input
            id="token"
            type="password"
            placeholder={tokenConfigured ? "Leave blank to keep existing token" : "Paste API token"}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoComplete="off"
          />
        </div>

        <div className={styles.checkboxField}>
          <input
            id="verifySSL"
            type="checkbox"
            checked={verifySSL}
            onChange={(e) => setVerifySSL(e.target.checked)}
          />
          <label htmlFor="verifySSL">Verify SSL certificate</label>
        </div>

        <div className={styles.actions}>
          <button type="submit" disabled={saveState === "saving"}>
            {saveState === "saving" ? "Saving…" : "Save"}
          </button>
          {saveState === "saved" && (
            <span className={styles.savedMsg}>Saved</span>
          )}
          {saveState === "error" && (
            <span className={styles.errorMsg}>{errorMsg}</span>
          )}
        </div>
      </form>
    </div>
  );
}
