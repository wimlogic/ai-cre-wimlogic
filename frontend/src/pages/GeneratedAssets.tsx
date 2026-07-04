import React, { useState, useEffect } from 'react';
import { generatedAssetService } from '../services/generatedAssetService';
import { GeneratedAsset } from '../types';
import { 
  FileCheck, 
  Search, 
  Download, 
  FileSpreadsheet, 
  RefreshCw, 
  SlidersHorizontal,
  ChevronRight,
  ExternalLink,
  Tag,
  Building2,
  Calendar,
  Layers
} from 'lucide-react';

export default function GeneratedAssets() {
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const loadAssets = async () => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await generatedAssetService.list({
        search: searchQuery || undefined,
        asset_type: typeFilter || undefined,
        limit: 100
      });
      setAssets(res.items || []);
    } catch (err) {
      console.error('Failed to list generated assets:', err);
      setErrorMsg('Error querying asset catalog database records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadAssets();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, typeFilter]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-sans font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <FileCheck className="w-5 h-5 text-indigo-600" />
            Generated Deliverables
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Access secure audit trails, site-plans, zoning reports, and architectural assets.
          </p>
        </div>
        <button
          onClick={loadAssets}
          className="p-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg transition-colors focus:outline-none animate-none"
          title="Refresh deliverables"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Control / Filter Bar */}
      <div className="bg-white border border-slate-100 rounded-xl p-4 shadow-sm flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search deliverables by name, APN, description, or project..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-slate-50/50"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-slate-200 rounded-lg text-xs px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Formats</option>
            <option value="PDF">PDF Report Document</option>
            <option value="CAD Model">Blueprint / CAD Model</option>
            <option value="Spreadsheet">Excel / Pro-Forma Worksheet</option>
            <option value="JSON">Raw Analytical Payload</option>
          </select>
          <button
            onClick={() => { setSearchQuery(''); setTypeFilter(''); }}
            className="px-3 py-2 border border-slate-200 text-slate-500 hover:bg-slate-50 rounded-lg text-xs transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-50 border-l-2 border-rose-500 text-rose-800 text-xs p-3.5 rounded-lg font-medium">
          {errorMsg}
        </div>
      )}

      {/* Asset grid */}
      {isLoading ? (
        <div className="py-24 flex justify-center items-center text-slate-400 text-xs font-mono uppercase tracking-widest">
          Polling asset lockers...
        </div>
      ) : assets.length === 0 ? (
        <div className="bg-white border border-slate-100 rounded-xl py-24 text-center text-slate-400 flex flex-col items-center justify-center space-y-3 shadow-sm">
          <FileSpreadsheet className="w-10 h-10 text-slate-200" />
          <span className="text-xs font-mono uppercase tracking-wider">No deliverables compiled</span>
          <p className="text-xs text-slate-400 max-w-sm">
            Deliverable records, PDFs, spreadsheets, and drawings generated from successful jobs will appear in this repository.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assets.map((asset) => (
            <div
              key={asset.asset_id}
              className="bg-white border border-slate-100 hover:border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex justify-between items-start mb-3">
                  <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-[10px] font-mono font-bold uppercase tracking-wider">
                    {asset.asset_type}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Ver: {asset.version || '1.0'}
                  </span>
                </div>

                <h3 className="font-sans font-bold text-slate-800 text-xs group-hover:text-indigo-600 transition-colors">
                  {asset.title || asset.file_name}
                </h3>

                <p className="text-xs text-slate-400 mt-1.5 line-clamp-2 min-h-[2rem]">
                  {asset.description || 'Deliverable asset generated through automated orchestration flow.'}
                </p>

                {/* File metrics metadata */}
                <div className="mt-4 pt-4 border-t border-slate-100 space-y-1.5 text-[11px] text-slate-500">
                  <div className="flex items-center gap-1.5 font-mono text-[10px]">
                    <Tag className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>File: <span className="text-slate-600 truncate max-w-[150px] inline-block align-bottom">{asset.file_name}</span></span>
                  </div>
                  {asset.file_size && (
                    <div className="flex items-center gap-1.5 font-mono text-[10px]">
                      <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>Size: <span className="text-slate-600">{Math.round(asset.file_size / 1024)} KB</span></span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                    <Calendar className="w-3.5 h-3.5 text-slate-300" />
                    <span>{new Date(asset.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              {/* Action Preview/Download */}
              <div className="mt-5 pt-3 border-t border-slate-100 flex justify-end">
                <a
                  href={asset.storage_path}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3.5 py-2 bg-slate-50 hover:bg-indigo-600 hover:text-white border border-slate-200 hover:border-indigo-600 rounded-lg text-xs font-semibold text-slate-600 transition-all flex items-center gap-1.5 focus:outline-none"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download File
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
