import { useEffect, useState } from "react";
import { fetchConfig, saveConfig, type ConfigRead } from "../../api/config";
import styles from "./SettingsPage.module.css";

type SaveState = "idle" | "saving" | "saved" | "error";

export default function SettingsPage() {
  const [url, setUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [secretConfigured, setSecretConfigured] = useState(false);
  const [verifySSL, setVerifySSL] = useState(true);
  const [debugLogging, setDebugLogging] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    fetchConfig()
      .then((cfg: ConfigRead) => {
        setUrl(cfg.clearpass_base_url ?? "");
        setClientId(cfg.clearpass_client_id ?? "");
        setVerifySSL(cfg.clearpass_verify_ssl);
        setDebugLogging(cfg.debug_logging);
        setSecretConfigured(cfg.clearpass_client_secret_configured);
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
        clearpass_client_id: clientId,
        clearpass_client_secret: clientSecret || undefined,
        clearpass_verify_ssl: verifySSL,
        debug_logging: debugLogging,
      });
      setSecretConfigured(cfg.clearpass_client_secret_configured);
      setClientSecret("");
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
            placeholder="https://clearpass.example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="clientId">Client ID</label>
          <input
            id="clientId"
            type="text"
            required
            placeholder="API client ID from ClearPass"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            autoComplete="off"
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="clientSecret">
            Client Secret
            {secretConfigured && (
              <span className={styles.tokenBadge}>configured</span>
            )}
          </label>
          <input
            id="clientSecret"
            type="password"
            placeholder={secretConfigured ? "Leave blank to keep existing secret" : "Client secret from ClearPass"}
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
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

        <div className={styles.checkboxField}>
          <input
            id="debugLogging"
            type="checkbox"
            checked={debugLogging}
            onChange={(e) => setDebugLogging(e.target.checked)}
          />
          <label htmlFor="debugLogging">Enable debug logging</label>
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
