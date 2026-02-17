import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState, useEffect, useCallback } from "react";
import { NavLink } from "react-router-dom";
const API = `${location.protocol}//${location.host}/api/v1`;
const PROVIDERS = [
    { id: "ollama", label: "Ollama", desc: "Local, free, private" },
    { id: "openai", label: "OpenAI", desc: "GPT-4o, o1, o3" },
    { id: "anthropic", label: "Anthropic", desc: "Claude Sonnet, Opus" },
];
const OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"];
const ANTHROPIC_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-5-20250514",
    "claude-haiku-4-5-20251001",
];
const DEFAULT_MODEL = {
    ollama: "llama3",
    openai: "gpt-4o",
    anthropic: "claude-sonnet-4-5-20250929",
};
function providerReady(id, s) {
    if (!s)
        return false;
    if (id === "ollama")
        return s.ollama_available;
    if (id === "openai")
        return s.openai_api_key_set;
    if (id === "anthropic")
        return s.anthropic_api_key_set;
    return false;
}
function modelsForProvider(id, s) {
    if (id === "ollama")
        return s?.ollama_models ?? [];
    if (id === "openai")
        return OPENAI_MODELS;
    if (id === "anthropic")
        return ANTHROPIC_MODELS;
    return [];
}
export function SettingsPage() {
    const [settings, setSettings] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState(null);
    const [provider, setProvider] = useState("anthropic");
    const [model, setModel] = useState("");
    const [anthropicKey, setAnthropicKey] = useState("");
    const [openaiKey, setOpenaiKey] = useState("");
    const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
    const [useCustomModel, setUseCustomModel] = useState(false);
    const switchProvider = (newProvider) => {
        setProvider(newProvider);
        const models = modelsForProvider(newProvider, settings);
        if (models.length > 0 && !models.includes(model)) {
            setModel(models[0]);
            setUseCustomModel(false);
        }
        else if (models.length === 0) {
            setModel(DEFAULT_MODEL[newProvider] ?? "");
            setUseCustomModel(true);
        }
    };
    const fetchSettings = useCallback(async () => {
        try {
            const res = await fetch(`${API}/settings`);
            if (res.ok) {
                const data = await res.json();
                setSettings(data);
                setProvider(data.provider);
                setModel(data.model);
                setOllamaUrl(data.ollama_url);
                setAnthropicKey("");
                setOpenaiKey("");
                const knownModels = modelsForProvider(data.provider, data);
                setUseCustomModel(knownModels.length > 0 && !knownModels.includes(data.model));
            }
        }
        catch { /* silent */ }
        finally {
            setLoading(false);
        }
    }, []);
    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);
    const showToast = (msg, ok) => {
        setToast({ msg, ok });
        setTimeout(() => setToast(null), 3000);
    };
    const handleSave = async () => {
        setSaving(true);
        try {
            const body = { provider, model };
            if (anthropicKey)
                body.anthropic_api_key = anthropicKey;
            if (openaiKey)
                body.openai_api_key = openaiKey;
            if (provider === "ollama")
                body.ollama_url = ollamaUrl;
            const res = await fetch(`${API}/settings`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (res.ok) {
                const data = await res.json();
                setSettings(data);
                setAnthropicKey("");
                setOpenaiKey("");
                showToast("Settings saved", true);
            }
            else {
                showToast("Failed to save settings", false);
            }
        }
        catch {
            showToast("Network error", false);
        }
        finally {
            setSaving(false);
        }
    };
    if (loading) {
        return (_jsx("div", { className: "settings-page", children: _jsx("div", { className: "page-loading", children: "Loading settings..." }) }));
    }
    const models = modelsForProvider(provider, settings);
    return (_jsxs("div", { className: "settings-page", children: [_jsxs("div", { className: "settings-header", children: [_jsx(NavLink, { to: "/", className: "settings-back", children: _jsx("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: _jsx("path", { d: "M12 4l-6 6 6 6" }) }) }), _jsxs("div", { children: [_jsx("h1", { className: "settings-title", children: "AI Settings" }), _jsx("p", { className: "settings-sub", children: "Configure the LLM provider used for gene research and synthesis" })] })] }), toast && (_jsx("div", { className: `settings-toast ${toast.ok ? "toast-ok" : "toast-err"}`, children: toast.msg })), _jsxs("div", { className: "settings-form", children: [_jsxs("div", { className: "settings-section", children: [_jsx("label", { className: "settings-label", children: "Provider" }), _jsx("div", { className: "provider-cards", children: PROVIDERS.map((p) => (_jsxs("button", { className: `provider-card ${provider === p.id ? "provider-card-active" : ""}`, onClick: () => switchProvider(p.id), type: "button", children: [_jsx("span", { className: "provider-card-name", children: p.label }), _jsx("span", { className: "provider-card-desc", children: p.desc }), settings && (_jsx("span", { className: `provider-dot ${providerReady(p.id, settings) ? "dot-ok" : "dot-off"}` }))] }, p.id))) })] }), _jsxs("div", { className: "settings-section", children: [_jsx("label", { className: "settings-label", htmlFor: "model-input", children: "Model" }), _jsxs(_Fragment, { children: [_jsxs("select", { id: "model-input", className: "settings-select", value: useCustomModel ? "__custom__" : model, onChange: (e) => {
                                        if (e.target.value === "__custom__") {
                                            setUseCustomModel(true);
                                            setModel("");
                                        }
                                        else {
                                            setUseCustomModel(false);
                                            setModel(e.target.value);
                                        }
                                    }, children: [...models.map((m) => (_jsx("option", { value: m, children: m }, m))), _jsx("option", { value: "__custom__", children: "Custom..." })] }), useCustomModel && (_jsx("input", { className: "settings-input settings-custom-model", type: "text", value: model, onChange: (e) => setModel(e.target.value), placeholder: "Enter custom model name" }))] })] }), (provider === "anthropic") && (_jsxs("div", { className: "settings-section", children: [_jsx("label", { className: "settings-label", htmlFor: "anthropic-key", children: "Anthropic API Key" }), _jsx("input", { id: "anthropic-key", className: "settings-input", type: "password", value: anthropicKey, onChange: (e) => setAnthropicKey(e.target.value), placeholder: settings?.anthropic_api_key_set ? "Key is set" : "sk-ant-..." })] })), (provider === "openai") && (_jsxs("div", { className: "settings-section", children: [_jsx("label", { className: "settings-label", htmlFor: "openai-key", children: "OpenAI API Key" }), _jsx("input", { id: "openai-key", className: "settings-input", type: "password", value: openaiKey, onChange: (e) => setOpenaiKey(e.target.value), placeholder: settings?.openai_api_key_set ? "Key is set" : "sk-..." })] })), provider === "ollama" && (_jsxs("div", { className: "settings-section", children: [_jsxs("label", { className: "settings-label", htmlFor: "ollama-url", children: ["Ollama URL", settings && (_jsx("span", { className: `ollama-status ${settings.ollama_available ? "status-ok" : "status-off"}`, children: settings.ollama_available ? "Connected" : "Unreachable" }))] }), _jsx("input", { id: "ollama-url", className: "settings-input", type: "text", value: ollamaUrl, onChange: (e) => setOllamaUrl(e.target.value), placeholder: "http://localhost:11434" })] })), _jsx("button", { className: "settings-save-btn", onClick: handleSave, disabled: saving, type: "button", children: saving ? "Saving..." : "Save Settings" })] })] }));
}
