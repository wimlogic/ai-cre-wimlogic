import React, { useState } from 'react';
import { AppConfig } from '../config/app';
import { apiClient } from '../services/apiClient';
import { 
  Settings as SettingsIcon, 
  Cpu, 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Globe, 
  Info,
  Server,
  Terminal,
  HeartHandshake
} from 'lucide-react';

export default function Settings() {
  const [testResult, setTestResult] = useState<'idle' | 'testing' | 'success' | 'failed'>('idle');
  const [testLog, setTestLog] = useState('');

  const handleTestConnection = async () => {
    setTestResult('testing');
    setTestLog('Handshaking with API base path...');
    try {
      // Hit a standard list endpoint to confirm router configuration is active
      const res = await apiClient.get<any>('/projects/?limit=1');
      setTestResult('success');
      setTestLog(`Connection established successfully!\nAPI Base URL: ${AppConfig.apiBaseUrl}\nActive database record count: ${res.count ?? 0}`);
    } catch (err: any) {
      console.error('Handshake failed:', err);
      setTestResult('failed');
      setTestLog(`Handshake failed.\nError: ${err.message || 'Network unreachable'}\nVerify the backend FastAPI server is active on Port 8000.`);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-sans font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-indigo-600" />
          System Settings
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Review application parameters, telemetry context, and server health checks.
        </p>
      </div>

      {/* Main Panels */}
      <div className="space-y-6">
        
        {/* Connection Profile Card */}
        <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-sm space-y-4">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 border-b border-slate-100 pb-2 mb-4 flex items-center gap-1.5">
            <Server className="w-4 h-4 text-indigo-500" />
            API Connection Profile
          </h2>

          <div className="space-y-3.5">
            <div className="grid grid-cols-3 gap-2.5 text-xs">
              <span className="text-slate-400 font-medium">Gateway Base URL</span>
              <span className="col-span-2 font-mono font-bold text-slate-800 break-all">
                {AppConfig.apiBaseUrl || 'Not Configured (Using Proxy)'}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-xs">
              <span className="text-slate-400 font-medium">Application Name</span>
              <span className="col-span-2 font-sans font-semibold text-slate-800">
                {AppConfig.appName || 'AI HOME WIMLOGIC'}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-xs">
              <span className="text-slate-400 font-medium">Build Version</span>
              <span className="col-span-2 font-mono text-slate-600">
                v{AppConfig.version || '1.0.0'}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-xs">
              <span className="text-slate-400 font-medium">Handshake Status</span>
              <span className="col-span-2 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span className="font-sans font-semibold text-slate-700">Online</span>
              </span>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
            <div className="flex items-center gap-2 text-[11px] text-slate-400 max-w-md">
              <Info className="w-4 h-4 text-indigo-500 shrink-0" />
              <span>Verify that your local dev environment variables correctly direct traffic to port 8000.</span>
            </div>

            <button
              onClick={handleTestConnection}
              disabled={testResult === 'testing'}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold tracking-wide transition-all shadow-md shadow-indigo-600/10 shrink-0 flex items-center justify-center gap-2 focus:outline-none"
            >
              <Activity className="w-4 h-4 animate-none" />
              {testResult === 'testing' ? 'VERIFYING...' : 'TEST GATEWAY'}
            </button>
          </div>
        </div>

        {/* Test Console Output */}
        {testResult !== 'idle' && (
          <div className="bg-slate-950 border border-slate-900 rounded-xl p-4 shadow-inner space-y-2">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2">
              <span className="text-[10px] font-mono font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
                <Terminal className="w-4 h-4 text-indigo-400" />
                HANDSHAKE FEEDBACK LOGS
              </span>
              {testResult === 'success' && (
                <span className="text-[9px] font-mono font-bold text-emerald-400 uppercase flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Handshake OK
                </span>
              )}
              {testResult === 'failed' && (
                <span className="text-[9px] font-mono font-bold text-rose-400 uppercase flex items-center gap-1">
                  <XCircle className="w-3.5 h-3.5" /> Handshake Failed
                </span>
              )}
            </div>
            <pre className="text-emerald-400 font-mono text-[11px] whitespace-pre-wrap leading-relaxed max-h-[150px] overflow-y-auto">
              {testLog}
            </pre>
          </div>
        )}

        {/* Support Section */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-5 flex gap-4">
          <div className="p-3 bg-white text-indigo-600 rounded-xl h-fit border border-slate-100 shrink-0">
            <HeartHandshake className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h3 className="font-sans font-bold text-slate-800 text-xs">
              System Admin Support
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              For issues connecting with production cloud clusters, database migration queries, or custom AI orchestration overrides, contact <span className="font-mono text-indigo-600 font-semibold">timg@kshoesusa.com</span>.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
