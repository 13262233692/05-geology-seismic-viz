import { useState, useEffect } from 'react';
import { SliceType, DownsampleMethod } from '../types';
import './ControlPanel.css';

export default function ControlPanel({
  files,
  selectedFile,
  onFileChange,
  metadata,
  onMetadataChange,
  sliceType,
  onSliceTypeChange,
  sliceValue,
  onSliceValueChange,
  zRange,
  onZRangeChange,
  maxTraces,
  onMaxTracesChange,
  maxSamples,
  onMaxSamplesChange,
  downsampleMethod,
  onDownsampleMethodChange,
  amplitudeScale,
  onAmplitudeScaleChange,
  onLoadData,
  onBuildIndex,
  isLoading,
  hasIndex,
}) {
  const [inlineValue, setInlineValue] = useState('');
  const [crosslineValue, setCrosslineValue] = useState('');

  useEffect(() => {
    if (metadata) {
      if (sliceType === SliceType.INLINE && !inlineValue) {
        setInlineValue(Math.floor((metadata.min_inline + metadata.max_inline) / 2));
      }
      if (sliceType === SliceType.CROSSLINE && !crosslineValue) {
        setCrosslineValue(Math.floor((metadata.min_crossline + metadata.max_crossline) / 2));
      }
    }
  }, [metadata, sliceType]);

  const handleSliceTypeChange = (e) => {
    const type = e.target.value;
    onSliceTypeChange(type);
    if (type === SliceType.INLINE) {
      onSliceValueChange(parseInt(inlineValue) || 0);
    } else if (type === SliceType.CROSSLINE) {
      onSliceValueChange(parseInt(crosslineValue) || 0);
    }
  };

  const handleInlineChange = (e) => {
    const value = e.target.value;
    setInlineValue(value);
    if (sliceType === SliceType.INLINE) {
      onSliceValueChange(parseInt(value) || 0);
    }
  };

  const handleCrosslineChange = (e) => {
    const value = e.target.value;
    setCrosslineValue(value);
    if (sliceType === SliceType.CROSSLINE) {
      onSliceValueChange(parseInt(value) || 0);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  };

  return (
    <div className="control-panel">
      <div className="panel-section">
        <h3>文件选择</h3>
        <select
          value={selectedFile}
          onChange={(e) => onFileChange(e.target.value)}
          className="form-select"
        >
          <option value="">-- 请选择SEG-Y文件 --</option>
          {files?.map((file) => (
            <option key={file.filename} value={file.filename}>
              {file.filename} ({formatFileSize(file.file_size)})
            </option>
          ))}
        </select>
        {selectedFile && (
          <button
            className="btn btn-secondary"
            onClick={() => onBuildIndex(selectedFile)}
            disabled={isLoading || hasIndex}
          >
            {hasIndex ? '✓ 已建立索引' : '建立索引'}
          </button>
        )}
      </div>

      {metadata && (
        <div className="panel-section">
          <h3>数据信息</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Inline范围:</span>
              <span className="info-value">{metadata.min_inline} - {metadata.max_inline}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Crossline范围:</span>
              <span className="info-value">{metadata.min_crossline} - {metadata.max_crossline}</span>
            </div>
            <div className="info-item">
              <span className="info-label">总道数:</span>
              <span className="info-value">{metadata.traces_count.toLocaleString()}</span>
            </div>
            <div className="info-item">
              <span className="info-label">每道采样点:</span>
              <span className="info-value">{metadata.samples_per_trace}</span>
            </div>
            <div className="info-item">
              <span className="info-label">采样间隔:</span>
              <span className="info-value">{metadata.sample_interval} ms</span>
            </div>
            <div className="info-item">
              <span className="info-label">时间范围:</span>
              <span className="info-value">0 - {metadata.z_max.toFixed(0)} ms</span>
            </div>
          </div>
        </div>
      )}

      <div className="panel-section">
        <h3>切片设置</h3>
        <div className="form-group">
          <label>切片类型</label>
          <select
            value={sliceType}
            onChange={handleSliceTypeChange}
            className="form-select"
          >
            <option value={SliceType.INLINE}>Inline 切片</option>
            <option value={SliceType.CROSSLINE}>Crossline 切片</option>
          </select>
        </div>

        {sliceType === SliceType.INLINE && (
          <div className="form-group">
            <label>
              Inline 值 ({metadata?.min_inline || 0} - {metadata?.max_inline || 0})
            </label>
            <input
              type="number"
              value={inlineValue}
              onChange={handleInlineChange}
              min={metadata?.min_inline || 0}
              max={metadata?.max_inline || 1000}
              className="form-input"
            />
          </div>
        )}

        {sliceType === SliceType.CROSSLINE && (
          <div className="form-group">
            <label>
              Crossline 值 ({metadata?.min_crossline || 0} - {metadata?.max_crossline || 0})
            </label>
            <input
              type="number"
              value={crosslineValue}
              onChange={handleCrosslineChange}
              min={metadata?.min_crossline || 0}
              max={metadata?.max_crossline || 1000}
              className="form-input"
            />
          </div>
        )}

        <div className="form-row">
          <div className="form-group">
            <label>Z轴起始 (ms)</label>
            <input
              type="number"
              value={zRange[0]}
              onChange={(e) => onZRangeChange([parseFloat(e.target.value) || 0, zRange[1]])}
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label>Z轴结束 (ms)</label>
            <input
              type="number"
              value={zRange[1]}
              onChange={(e) => onZRangeChange([zRange[0], parseFloat(e.target.value) || 0])}
              className="form-input"
            />
          </div>
        </div>
      </div>

      <div className="panel-section">
        <h3>显示设置</h3>
        <div className="form-group">
          <label>最大道数</label>
          <input
            type="number"
            value={maxTraces}
            onChange={(e) => onMaxTracesChange(parseInt(e.target.value) || 800)}
            min="100"
            max="2000"
            step="100"
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label>最大采样点数</label>
          <input
            type="number"
            value={maxSamples}
            onChange={(e) => onMaxSamplesChange(parseInt(e.target.value) || 500)}
            min="100"
            max="2000"
            step="100"
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label>下采样方法</label>
          <select
            value={downsampleMethod}
            onChange={(e) => onDownsampleMethodChange(e.target.value)}
            className="form-select"
          >
            <option value={DownsampleMethod.AVERAGE}>平均值</option>
            <option value={DownsampleMethod.MAX}>最大值</option>
            <option value={DownsampleMethod.MIN}>最小值</option>
            <option value={DownsampleMethod.DECIMATE}>抽取</option>
          </select>
        </div>

        <div className="form-group">
          <label>振幅缩放: {amplitudeScale.toFixed(1)}x</label>
          <input
            type="range"
            value={amplitudeScale}
            onChange={(e) => onAmplitudeScaleChange(parseFloat(e.target.value))}
            min="0.1"
            max="3"
            step="0.1"
            className="form-range"
          />
        </div>
      </div>

      <button
        className="btn btn-primary"
        onClick={onLoadData}
        disabled={isLoading || !selectedFile || !hasIndex}
      >
        {isLoading ? '加载中...' : '加载数据'}
      </button>
    </div>
  );
}
