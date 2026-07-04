import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Cpu, 
  KeyRound, 
  Database, 
  CheckCircle2, 
  AlertCircle,
  Save,
  Link,
  Info,
  RefreshCw
} from 'lucide-react';
import { CreApi } from '../lib/api';

export default function CreSettings() {
  const [devtoolsEndpoint, setDevtoolsEndpoint] = useState('https://devtools-gateway.wimlogic.net/api/v1');
  const [googleMapsKey, setGoogleMapsKey] = useState('AIzaSyD_EXAMPLE_KEY_FOR_MOCK');
  const [mlsEnabled, setMlsEnabled] = useState(true);
  const [autoTrigger, setAutoTrigger] = useState(false);
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    async function loadSettings() {
      try {
        setLoading(true);
        const res = await CreApi.getSettings();
        if (res.status === 200) {
          setDevtoolsEndpoint(res.data.devtools_endpoint || '');
          setGoogleMapsKey(res.data.google_maps_api_key || '');
          setMlsEnabled(res.data.mls_integration_enabled ?? true);
          setAutoTrigger(res.data.auto_trigger_workflow ?? false);
        }
      } catch (err) {
        console.error("Failed to load systems configurations:", err);
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    try {
      setSaving(true);
      await CreApi.updateSettings({
        devtools_endpoint: devtoolsEndpoint,
        google_maps_api_key: googleMapsKey,
        mls_integration_enabled: mlsEnabled,
        auto_trigger_workflow: autoTrigger
      });
      setStatusMsg({ type: 'success', text: 'Enterprise configurations saved securely to local JSON core.' });
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to update system parameters.' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-6 h-6 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"></div>
        <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Synchronizing configuration stack...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div>
        <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">Enterprise Settings</h2>
        <p className="text-slate-500 text-xs mt-1">
          Configure corporate API endpoints, external database links, Google Maps credentials, and automated workflow triggers.
        </p>
      </div>

      <form onSubmit={handleSaveSettings} className="bg-white border border-slate-100 rounded-xl shadow-sm overflow-hidden divide-y divide-slate-100">
        <div className="p-6 space-y-5">
          {statusMsg && (
            <div className={`p-4 rounded-lg text-xs flex items-center gap-2.5 ${
              statusMsg.type === 'success' 
                ? 'bg-emerald-50 border border-emerald-100 text-emerald-800' 
                : 'bg-rose-50 border border-rose-100 text-rose-800'
            }`}>
              {statusMsg.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{statusMsg.text}</span>
            </div>
          )}

          {/* Gateway Endpoint */}
          <div className="space-y-2">
            <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase flex items-center gap-1.5 font-mono">
              <Cpu className="w-3.5 h-3.5 text-indigo-500" />
              <span>DEV-TOOLS Orchestration Gateway</span>
            </label>
            <input
              type="url"
              required
              value={devtoolsEndpoint}
              onChange={(e) => setDevtoolsEndpoint(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
            />
            <p className="text-[10px] text-slate-400 leading-normal">
              Separate gateway REST API route for dispatching multi-agent instructions and tracking event logs.
            </p>
          </div>

          {/* Maps API Key */}
          <div className="space-y-2">
            <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase flex items-center gap-1.5 font-mono">
              <KeyRound className="w-3.5 h-3.5 text-indigo-500" />
              <span>Google Maps Static & StreetView Key</span>
            </label>
            <input
              type="password"
              required
              value={googleMapsKey}
              onChange={(e) => setGoogleMapsKey(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-indigo-500 font-mono"
            />
            <p className="text-[10px] text-slate-400 leading-normal">
              Required for fetching real-time parcel satellite bounds, Street View imagery, and coordinate lookups.
            </p>
          </div>

          {/* MLS Database Toggle */}
          <div className="space-y-4 pt-2">
            <label className="text-[10px] font-bold text-slate-500 tracking-wider uppercase flex items-center gap-1.5 font-mono">
              <Database className="w-3.5 h-3.5 text-indigo-500" />
              <span>Enterprise Sync Toggles</span>
            </label>

            <div className="space-y-3">
              {/* Toggle 1 */}
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-800 block">County MLS Integration Indexing</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Allow auto-synchronization of registered parcel APNs with county database records.</span>
                </div>
                <button
                  type="button"
                  onClick={() => setMlsEnabled(!mlsEnabled)}
                  className={`w-11 h-6 rounded-full transition-colors focus:outline-none relative ${
                    mlsEnabled ? 'bg-indigo-600' : 'bg-slate-200'
                  }`}
                >
                  <span className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full shadow-sm transition-transform ${
                    mlsEnabled ? 'translate-x-5' : 'translate-x-0'
                  }`}></span>
                </button>
              </div>

              {/* Toggle 2 */}
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-800 block">Immediate Auto-Trigger Pipelines</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Automatically trigger feasibility and zoning checks immediately upon property registration.</span>
                </div>
                <button
                  type="button"
                  onClick={() => setAutoTrigger(!autoTrigger)}
                  className={`w-11 h-6 rounded-full transition-colors focus:outline-none relative ${
                    autoTrigger ? 'bg-indigo-600' : 'bg-slate-200'
                  }`}
                >
                  <span className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full shadow-sm transition-transform ${
                    autoTrigger ? 'translate-x-5' : 'translate-x-0'
                  }`}>
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer row */}
        <div className="p-6 bg-slate-50/50 flex items-center justify-between">
          <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <Info className="w-3.5 h-3.5 text-slate-300" />
            <span>AI-CRE WIMLOGIC v1.0.0-PROD</span>
          </span>
          <button
            type="submit"
            id="save-settings-btn"
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-sans font-semibold text-xs rounded-lg transition-colors focus:outline-none shadow-sm shadow-indigo-600/10"
          >
            {saving ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            <span>Save Configurations</span>
          </button>
        </div>
      </form>
    </div>
  );
}
