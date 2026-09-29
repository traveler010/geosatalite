import { useState, useRef, useCallback } from 'react';
import { Upload, FileCheck, AlertTriangle, Image, X, ChevronRight, Layers, Radar, Eye } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { uploadImages } from '../services/api';
import { useNavigate } from 'react-router-dom';

export default function UploadWorkspace() {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previewUrls, setPreviewUrls] = useState([]);
  const [modalityHints, setModalityHints] = useState(['', '']);
  const fileInputRef = useRef(null);
  const { actions } = useAppStore();
  const navigate = useNavigate();

  const handleFiles = useCallback((files) => {
    const fileArray = Array.from(files).slice(0, 2);
    setSelectedFiles(fileArray);
    setUploadResult(null);

    // Generate previews
    const urls = [];
    fileArray.forEach((file) => {
      const url = URL.createObjectURL(file);
      urls.push(url);
    });
    setPreviewUrls(urls);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleUpload = useCallback(async () => {
    if (!selectedFiles.length || uploading) return;
    setUploading(true);

    try {
      const result = await uploadImages(selectedFiles, modalityHints.filter(Boolean).join(','));
      setUploadResult(result);

      // Store in app state
      actions.setUploadValidation(result);

      if (result.compatibility?.valid) {
        actions.addMessage('assistant',
          `${selectedFiles.length} image(s) uploaded and validated. Detected: ${result.compatibility.input_type}, modality: ${result.compatibility.modality || 'auto-detected'}.`,
          'UPLOAD / VALIDATION PASSED'
        );

        // Phase 4: Automatically animate globe to detected coordinates if georeferenced
        const geo = result.geospatial_metadata?.[0] || result.compatibility?.metadata?.geospatial;
        if (geo?.bounds_wgs84) {
          const b = geo.bounds_wgs84;
          const lat = (b.min_lat + b.max_lat) / 2;
          const lon = (b.min_lon + b.max_lon) / 2;
          actions.lockLocation({
            location: { latitude: lat, longitude: lon, altitude: 4000 },
            label: selectedFiles[0]?.name || 'Uploaded Satellite Scene',
            sensor: geo.is_multispectral ? 'Multispectral (10m)' : geo.modality === 'sar' ? 'SAR Sentinel-1' : 'High-Res Optical',
            source: 'Embedded GeoTIFF Header',
            confidence: 0.99,
            crs: geo.crs || 'WGS84 / EPSG:4326',
          });
        }
      }
    } catch (err) {
      setUploadResult({
        compatibility: {
          valid: false,
          errors: ['Backend unavailable. Start the backend server: uvicorn backend.main:app --reload'],
        },
      });
    } finally {
      setUploading(false);
    }
  }, [selectedFiles, uploading, modalityHints, actions]);

  const clearFiles = () => {
    setSelectedFiles([]);
    setPreviewUrls([]);
    setUploadResult(null);
    setModalityHints(['', '']);
  };

  const proceedToQuery = () => {
    if (uploadResult?.file_paths) {
      actions.setUploadedPaths(uploadResult.file_paths);
    }
    navigate('/query');
  };

  const compat = uploadResult?.compatibility;

  return (
    <section className="max-w-[1200px] mx-auto">
      <div className="grid grid-cols-[1fr_380px] gap-4 max-lg:grid-cols-1">
        {/* Left: Upload Zone */}
        <div className="glass rounded-[14px] overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-border bg-panel-solid/95">
            <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-faint">
              Image Upload & Validation
            </span>
            <strong className="block mt-1 text-sm font-bold text-text">
              Upload Satellite Imagery
            </strong>
            <p className="mt-1 text-[11px] text-muted">
              Upload 1–2 images: a single image, a bi-temporal pair, or an optical+SAR pair.
              Supports GeoTIFF, TIFF, PNG, JPEG.
            </p>
          </div>

          <div className="flex-1 p-5">
            {/* Drop Zone */}
            <div
              className={`relative flex flex-col items-center justify-center min-h-[280px] rounded-xl border-2 border-dashed transition-all duration-300 cursor-pointer ${
                dragOver
                  ? 'border-blue-bright bg-blue/10 scale-[1.01]'
                  : selectedFiles.length
                  ? 'border-emerald/40 bg-emerald/5'
                  : 'border-border-light hover:border-blue-bright/50 hover:bg-panel-hover/50'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => !selectedFiles.length && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.tif,.tiff"
                multiple
                onChange={(e) => handleFiles(e.target.files)}
                className="hidden"
              />

              {selectedFiles.length > 0 ? (
                <div className="w-full px-6">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-emerald text-xs font-medium flex items-center gap-1.5">
                      <FileCheck className="w-4 h-4" />
                      {selectedFiles.length} file(s) selected
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); clearFiles(); }}
                      className="p-1 rounded-md hover:bg-panel-hover text-muted hover:text-text transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Previews */}
                  <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
                    {selectedFiles.map((file, i) => (
                      <div key={i} className="relative rounded-lg overflow-hidden border border-border bg-bg-deep">
                        {previewUrls[i] && (
                          <img
                            src={previewUrls[i]}
                            alt={file.name}
                            className="w-full h-[160px] object-cover"
                          />
                        )}
                        <div className="p-2.5">
                          <p className="text-[11px] text-text font-medium truncate">{file.name}</p>
                          <p className="text-[10px] text-muted mt-0.5">
                            {(file.size / 1024).toFixed(1)} KB
                          </p>
                          {/* Modality Hint */}
                          <select
                            value={modalityHints[i]}
                            onChange={(e) => {
                              const newHints = [...modalityHints];
                              newHints[i] = e.target.value;
                              setModalityHints(newHints);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="mt-2 w-full h-7 px-2 border border-border-light rounded-md bg-panel-input text-text text-[10px] outline-none"
                          >
                            <option value="">Auto-detect modality</option>
                            <option value="optical">Optical RGB</option>
                            <option value="sar">SAR (Radar)</option>
                            <option value="multispectral">Multispectral</option>
                          </select>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center px-6">
                  <Upload className="w-10 h-10 mx-auto mb-3 text-muted" />
                  <p className="text-sm text-text font-medium">
                    Drop images here or click to browse
                  </p>
                  <p className="mt-1.5 text-[11px] text-muted">
                    GeoTIFF · TIFF · PNG · JPEG — max 2 images
                  </p>
                </div>
              )}
            </div>

            {/* Upload Button */}
            {selectedFiles.length > 0 && !uploadResult && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="mt-4 w-full h-[42px] rounded-lg border border-blue-bright bg-blue text-white text-sm font-semibold hover:bg-blue-hover transition-all disabled:opacity-60 disabled:cursor-wait flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin-slow" />
                    Validating...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Upload & Validate
                  </>
                )}
              </button>
            )}

            {/* Proceed to Query */}
            {compat?.valid && (
              <button
                onClick={proceedToQuery}
                className="mt-3 w-full h-[42px] rounded-lg border border-emerald bg-emerald/15 text-emerald-light text-sm font-semibold hover:bg-emerald/25 transition-all flex items-center justify-center gap-2"
              >
                Proceed to Query Workspace
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Right: Compatibility Results */}
        <div className="glass rounded-[14px] overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-border bg-panel-solid/95">
            <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-faint">
              Input Compatibility Checker
            </span>
            <strong className="block mt-1 text-sm font-bold text-text">
              Validation Results
            </strong>
          </div>

          <div className="flex-1 p-5 space-y-3">
            {!uploadResult ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <Eye className="w-8 h-8 text-faint mb-3" />
                <p className="text-xs text-muted">
                  Upload images to see validation results
                </p>
              </div>
            ) : (
              <>
                {/* Status Badge */}
                <div className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border ${
                  compat?.valid
                    ? 'border-emerald/30 bg-emerald/10'
                    : 'border-red-500/30 bg-red-500/10'
                }`}>
                  {compat?.valid ? (
                    <FileCheck className="w-4 h-4 text-emerald" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                  )}
                  <span className={`text-xs font-semibold ${
                    compat?.valid ? 'text-emerald-light' : 'text-red-300'
                  }`}>
                    {compat?.valid ? 'VALIDATION PASSED' : 'VALIDATION FAILED'}
                  </span>
                </div>

                {/* Details Grid */}
                {compat?.valid && (
                  <div className="space-y-2">
                    <DetailRow label="Input Type" value={compat.input_type} icon={Layers} />
                    <DetailRow label="Modality" value={compat.modality || 'auto-detected'} icon={Radar} />
                    <DetailRow
                      label="Format"
                      value={compat.metadata?.format?.toUpperCase() || 'detected'}
                      icon={Image}
                    />
                    {compat.metadata?.width && (
                      <DetailRow
                        label="Dimensions"
                        value={`${compat.metadata.width} × ${compat.metadata.height}`}
                        icon={Image}
                      />
                    )}
                    {compat.metadata?.bands && (
                      <DetailRow
                        label="Bands"
                        value={`${compat.metadata.bands} (${compat.metadata.band_names?.join(', ')})`}
                        icon={Layers}
                      />
                    )}
                    {compat.metadata?.is_georeferenced !== undefined && (
                      <DetailRow
                        label="Georeferenced"
                        value={compat.metadata.is_georeferenced ? 'Yes' : 'No'}
                        icon={Radar}
                      />
                    )}
                  </div>
                )}

                {/* Errors */}
                {compat?.errors?.length > 0 && (
                  <div className="space-y-1.5">
                    {compat.errors.map((err, i) => (
                      <div key={i} className="flex gap-2 px-3 py-2 rounded-lg border border-red-500/20 bg-red-500/5">
                        <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                        <p className="text-[11px] text-red-300">{err}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Warnings */}
                {compat?.warnings?.length > 0 && (
                  <div className="space-y-1.5">
                    {compat.warnings.map((warn, i) => (
                      <div key={i} className="flex gap-2 px-3 py-2 rounded-lg border border-gold/20 bg-gold/5">
                        <AlertTriangle className="w-3.5 h-3.5 text-gold shrink-0 mt-0.5" />
                        <p className="text-[11px] text-gold-light">{warn}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* File Info */}
                {uploadResult.files && (
                  <div className="pt-2">
                    <p className="font-mono text-[9px] tracking-[0.08em] uppercase text-faint mb-2">
                      Uploaded Files
                    </p>
                    {uploadResult.files.map((f, i) => (
                      <div key={i} className="px-3 py-2 mb-1.5 rounded-lg border border-border bg-panel-card">
                        <p className="text-[11px] text-text font-medium truncate">{f.original_name}</p>
                        <p className="text-[10px] text-muted mt-0.5">
                          {(f.size_bytes / 1024).toFixed(1)} KB · {f.content_type}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function DetailRow({ label, value, icon: Icon }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg border border-border bg-panel-card">
      <Icon className="w-3.5 h-3.5 text-faint shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-[10px] text-faint font-mono uppercase">{label}</span>
        <p className="text-[11px] text-text font-medium truncate">{value}</p>
      </div>
    </div>
  );
}
