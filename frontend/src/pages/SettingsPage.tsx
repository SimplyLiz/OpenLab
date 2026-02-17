import { useState, useEffect, useCallback } from "react";
import { NavLink } from "react-router-dom";

const API = `${location.protocol}//${location.host}/api/v1`;

interface Settings {
  provider: string;
  model: string;
  anthropic_api_key_set: boolean;
  openai_api_key_set: boolean;
  ollama_url: string;
  ollama_available: boolean;
  ollama_models: string[];
}

const PROVIDERS = [
  { id: "ollama", label: "Ollama", desc: "Local, free, private" },
  { id: "openai", label: "OpenAI", desc: "GPT-4o, o1, o3" },
  { id: "anthropic", label: "Anthropic", desc: "Claude Sonnet, Opus" },
] as const;

const OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"];
const ANTHROPIC_MODELS = [
  "claude-sonnet-4-5-20250929",
  "claude-opus-4-5-20250514",
  "claude-haiku-4-5-20251001",
];

const DEFAULT_MODEL: Record<string, string> = {
  ollama: "llama3",
  openai: "gpt-4o",
  anthropic: "claude-sonnet-4-5-20250929",
};

function providerReady(
  id: string,
  s: Settings | null,
): boolean {
  if (!s) return false;
  if (id === "ollama") return s.ollama_available;
  if (id === "openai") return s.openai_api_key_set;
  if (id === "anthropic") return s.anthropic_api_key_set;
  return false;
}

function modelsForProvider(
  id: string,
  s: Settings | null,
): string[] {
  if (id === "ollama") return s?.ollama_models ?? [];
  if (id === "openai") return OPENAI_MODELS;
  if (id === "anthropic") return ANTHROPIC_MODELS;
  return [];
}

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  // Form state
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [useCustomModel, setUseCustomModel] = useState(false);

  const switchProvider = (newProvider: string) => {
    setProvider(newProvider);
    const models = modelsForProvider(newProvider, settings);
    if (models.length > 0 && !models.includes(model)) {
      setModel(models[0]);
      setUseCustomModel(false);
    } else if (models.length === 0) {
      setModel(DEFAULT_MODEL[newProvider] ?? "");
      setUseCustomModel(true);
    }
  };

  const fetchSettings = useCallback(async () => {
    try {
      const res = await fetch(`${API}/settings`);
      if (res.ok) {
        const data: Settings = await res.json();
        setSettings(data);
        setProvider(data.provider);
        setModel(data.model);
        setOllamaUrl(data.ollama_url);
        setAnthropicKey("");
        setOpenaiKey("");
        const knownModels = modelsForProvider(data.provider, data);
        setUseCustomModel(knownModels.length > 0 && !knownModels.includes(data.model));
      }
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const body: Record<string, string> = { provider, model };
      if (anthropicKey) body.anthropic_api_key = anthropicKey;
      if (openaiKey) body.openai_api_key = openaiKey;
      if (provider === "ollama") body.ollama_url = ollamaUrl;

      const res = await fetch(`${API}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const data: Settings = await res.json();
        setSettings(data);
        setAnthropicKey("");
        setOpenaiKey("");
        showToast("Settings saved", true);
      } else {
        showToast("Failed to save settings", false);
      }
    } catch {
      showToast("Network error", false);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-page">
        <div className="page-loading">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-header">
        <NavLink to="/" className="settings-back">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 4l-6 6 6 6" />
          </svg>
        </NavLink>
        <div>
          <h1 className="settings-title">AI Settings</h1>
          <p className="settings-sub">Configure the LLM provider used for gene research and synthesis</p>
        </div>
      </div>

      {toast && (
        <div className={`settings-toast ${toast.ok ? "toast-ok" : "toast-err"}`}>
          {toast.msg}
        </div>
      )}

      <div className="settings-form">
        {/* Provider selector */}
        <div className="settings-section">
          <label className="settings-label">Provider</label>
          <div className="provider-cards">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                className={`provider-card ${provider === p.id ? "provider-card-active" : ""}`}
                onClick={() => switchProvider(p.id)}
                type="button"
              >
                <span className="provider-card-name">{p.label}</span>
                <span className="provider-card-desc">{p.desc}</span>
                {settings && (
                  <span className={`provider-dot ${providerReady(p.id, settings) ? "dot-ok" : "dot-off"}`} />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Model */}
        <div className="settings-section">
          <label className="settings-label" htmlFor="model-input">Model</label>
          {(() => {
            const models = modelsForProvider(provider, settings);
            return (
              <>
                <select
                  id="model-input"
                  className="settings-select"
                  value={useCustomModel ? "__custom__" : model}
                  onChange={(e) => {
                    if (e.target.value === "__custom__") {
                      setUseCustomModel(true);
                      setModel("");
                    } else {
                      setUseCustomModel(false);
                      setModel(e.target.value);
                    }
                  }}
                >
                  {models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                  <option value="__custom__">Custom...</option>
                </select>
                {useCustomModel && (
                  <input
                    className="settings-input settings-custom-model"
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="Enter custom model name"
                  />
                )}
              </>
            );
          })()}
        </div>

        {/* Anthropic API key */}
        {(provider === "anthropic") && (
          <div className="settings-section">
            <label className="settings-label" htmlFor="anthropic-key">Anthropic API Key</label>
            <input
              id="anthropic-key"
              className="settings-input"
              type="password"
              value={anthropicKey}
              onChange={(e) => setAnthropicKey(e.target.value)}
              placeholder={settings?.anthropic_api_key_set ? "Key is set" : "sk-ant-..."}
            />
          </div>
        )}

        {/* OpenAI API key */}
        {(provider === "openai") && (
          <div className="settings-section">
            <label className="settings-label" htmlFor="openai-key">OpenAI API Key</label>
            <input
              id="openai-key"
              className="settings-input"
              type="password"
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              placeholder={settings?.openai_api_key_set ? "Key is set" : "sk-..."}
            />
          </div>
        )}

        {/* Ollama URL */}
        {provider === "ollama" && (
          <div className="settings-section">
            <label className="settings-label" htmlFor="ollama-url">
              Ollama URL
              {settings && (
                <span className={`ollama-status ${settings.ollama_available ? "status-ok" : "status-off"}`}>
                  {settings.ollama_available ? "Connected" : "Unreachable"}
                </span>
              )}
            </label>
            <input
              id="ollama-url"
              className="settings-input"
              type="text"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
              placeholder="http://localhost:11434"
            />
          </div>
        )}

        {/* Save */}
        <button
          className="settings-save-btn"
          onClick={handleSave}
          disabled={saving}
          type="button"
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
