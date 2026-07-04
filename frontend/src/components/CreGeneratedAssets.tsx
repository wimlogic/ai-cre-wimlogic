import { useState, useEffect } from 'react';
import { 
  Download, 
  FileText, 
  FileSpreadsheet, 
  FileImage, 
  FileCheck, 
  Search, 
  Calendar, 
  HardDrive,
  ExternalLink,
  Tag
} from 'lucide-react';
import { CreGeneratedAsset, CreProperty } from '../types';
import { CreApi } from '../lib/api';

export default function CreGeneratedAssets() {
  const [assets, setAssets] = useState<CreGeneratedAsset[]>([]);
  const [properties, setProperties] = useState<CreProperty[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAssets() {
      try {
        setLoading(true);
        const [propRes, assetRes] = await Promise.all([
          CreApi.getProperties(),
          CreApi.getGeneratedAssets(selectedPropertyId !== 'all' ? { property_id: Number(selectedPropertyId) } : undefined)
        ]);
        setProperties(propRes.items);
        setAssets(assetRes.items);
      } catch (err) {
        console.error("Failed to load generated assets:", err);
      } finally {
        setLoading(false);
      }
    }
    loadAssets();
  }, [selectedPropertyId]);

  const filteredAssets = assets.filter(asset => 
    (asset.title && asset.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (asset.description && asset.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (asset.file_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'spreadsheet':
        return <FileSpreadsheet className="w-5 h-5 text-emerald-500" />;
      case 'image':
        return <FileImage className="w-5 h-5 text-blue-500" />;
      case 'pdf':
        return <FileText className="w-5 h-5 text-rose-500" />;
      default:
        return <FileCheck className="w-5 h-5 text-slate-500" />;
    }
  };

  const formatBytes = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold tracking-tight text-slate-900">Generated Assets Index</h2>
          <p className="text-slate-500 text-xs mt-1">
            Access, inspect, and extract multi-agent reports, pro-forma spreadsheets, and structural conceptual designs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-wider">FILTER PARCEL:</label>
          <select
            value={selectedPropertyId}
            onChange={(e) => setSelectedPropertyId(e.target.value)}
            className="px-3 py-1.5 bg-white border border-slate-200/80 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none"
          >
            <option value="all">-- All Parcels --</option>
            {properties.map(p => (
              <option key={p.id} value={p.id}>{p.display_address} ({p.property_uid})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-100 p-4 rounded-xl shadow-sm flex flex-col sm:flex-row gap-4 items-center">
        <div className="relative w-full sm:flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            id="asset-search-input"
            type="text"
            placeholder="Search assets by file title, category, extension..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200/80 rounded-lg text-xs placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] text-slate-400 tracking-wider">
          <span>COMPILED DOCUMENTS:</span>
          <span className="font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200/40">
            {filteredAssets.length} TOTAL
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="w-6 h-6 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"></div>
          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Indexing asset register...</span>
        </div>
      ) : filteredAssets.length === 0 ? (
        <div className="bg-white border border-slate-100 p-12 text-center rounded-xl shadow-sm flex flex-col items-center justify-center space-y-4">
          <HardDrive className="w-10 h-10 text-slate-300" />
          <div>
            <h4 className="text-slate-800 font-sans font-semibold text-sm">No Assets Generated</h4>
            <p className="text-slate-400 text-xs mt-1">
              Run active multi-agent pipeline executions to generate downloadable pro-forma documents and feasibility PDFs.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredAssets.map((asset) => (
            <div
              key={asset.asset_id}
              id={`asset-card-${asset.asset_id}`}
              className="bg-white border border-slate-100 rounded-xl p-5 shadow-sm hover:shadow-md/5 hover:border-slate-200 transition-all flex flex-col sm:flex-row gap-4 items-start"
            >
              {/* Asset Thumbnail or icon */}
              <div className="w-14 h-14 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 shadow-inner">
                {asset.thumbnail_path ? (
                  <img 
                    src={asset.thumbnail_path} 
                    alt={asset.title} 
                    className="w-full h-full object-cover rounded-lg"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  getFileIcon(asset.asset_type)
                )}
              </div>

              <div className="space-y-2 flex-1 min-w-0">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="bg-slate-100 text-slate-600 font-mono text-[8px] font-bold px-1.5 py-0.2 rounded uppercase border border-slate-200/50">
                      {asset.asset_category || 'Feasibility'}
                    </span>
                    <span className="text-[9px] text-slate-400 font-mono">VER: {asset.version || '1.0.0'}</span>
                  </div>
                  <h3 className="font-sans font-bold text-xs text-slate-800 truncate leading-tight">
                    {asset.title || asset.file_name}
                  </h3>
                  <p className="text-slate-500 text-[11px] leading-relaxed line-clamp-2">
                    {asset.description || 'System compiled feasibility asset.'}
                  </p>
                </div>

                {/* Meta row */}
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-100/60 mt-1">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-300" />
                    <span>{asset.created_at.slice(0, 10)}</span>
                  </span>
                  <span>{formatBytes(asset.file_size)}</span>
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      window.alert(`Simulating secure download for ${asset.file_name} via separate corporate file store...`);
                    }}
                    className="text-indigo-600 hover:text-indigo-800 flex items-center gap-1 font-sans font-bold transition-colors"
                  >
                    <span>Extract</span>
                    <Download className="w-3 h-3" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
