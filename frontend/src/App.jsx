import { useState, useEffect, useCallback } from 'react';
import ControlPanel from './components/ControlPanel';
import WigglePlot from './components/WigglePlot';
import { fetchFiles, fetchMetadata, buildIndex, fetchSlice } from './services/api';
import { SliceType, DownsampleMethod } from './types';
import './App.css';

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [hasIndex, setHasIndex] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [sliceType, setSliceType] = useState(SliceType.INLINE);
  const [sliceValue, setSliceValue] = useState(0);
  const [zRange, setZRange] = useState([0, 1000]);
  const [maxTraces, setMaxTraces] = useState(800);
  const [maxSamples, setMaxSamples] = useState(500);
  const [downsampleMethod, setDownsampleMethod] = useState(DownsampleMethod.AVERAGE);
  const [amplitudeScale, setAmplitudeScale] = useState(1.0);

  const [seismicData, setSeismicData] = useState(null);
  const [viewState, setViewState] = useState({ offsetX: 0, offsetY: 0, zoom: 1 });

  useEffect(() => {
    loadFiles();
  }, []);

  useEffect(() => {
    if (metadata) {
      setZRange([0, metadata.z_max]);
    }
  }, [metadata]);

  const loadFiles = async () => {
    try {
      const response = await fetchFiles();
      setFiles(response.files);
      if (response.files.length > 0) {
        setSelectedFile(response.files[0].filename);
        setHasIndex(response.files[0].has_index);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleFileChange = async (filename) => {
    setSelectedFile(filename);
    setMetadata(null);
    setSeismicData(null);
    setError(null);
    
    const fileInfo = files.find(f => f.filename === filename);
    setHasIndex(fileInfo?.has_index || false);

    if (filename && fileInfo?.has_index) {
      try {
        setIsLoading(true);
        const meta = await fetchMetadata(filename);
        setMetadata(meta);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleBuildIndex = async (filename) => {
    try {
      setIsLoading(true);
      setError(null);
      await buildIndex(filename);
      setHasIndex(true);
      const meta = await fetchMetadata(filename);
      setMetadata(meta);
      await loadFiles();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadData = useCallback(async () => {
    if (!selectedFile || !hasIndex) return;

    try {
      setIsLoading(true);
      setError(null);

      const request = {
        filename: selectedFile,
        slice_type: sliceType,
        slice_value: sliceValue,
        z_range: zRange[0] > 0 || zRange[1] < metadata?.z_max ? zRange : null,
        max_traces: maxTraces,
        max_samples: maxSamples,
        downsample_method: downsampleMethod,
      };

      const data = await fetchSlice(request);
      setSeismicData(data);
      setViewState({ offsetX: 0, offsetY: 0, zoom: 1 });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [selectedFile, hasIndex, sliceType, sliceValue, zRange, maxTraces, maxSamples, downsampleMethod, metadata]);

  const handleViewChange = useCallback((newView) => {
    setViewState(newView);
  }, []);

  return (
    <div className="app-container">
      <ControlPanel
        files={files}
        selectedFile={selectedFile}
        onFileChange={handleFileChange}
        metadata={metadata}
        onMetadataChange={setMetadata}
        sliceType={sliceType}
        onSliceTypeChange={setSliceType}
        sliceValue={sliceValue}
        onSliceValueChange={setSliceValue}
        zRange={zRange}
        onZRangeChange={setZRange}
        maxTraces={maxTraces}
        onMaxTracesChange={setMaxTraces}
        maxSamples={maxSamples}
        onMaxSamplesChange={setMaxSamples}
        downsampleMethod={downsampleMethod}
        onDownsampleMethodChange={setDownsampleMethod}
        amplitudeScale={amplitudeScale}
        onAmplitudeScaleChange={setAmplitudeScale}
        onLoadData={handleLoadData}
        onBuildIndex={handleBuildIndex}
        isLoading={isLoading}
        hasIndex={hasIndex}
      />

      <div className="main-content">
        <header className="app-header">
          <h1>地震波数据分析系统</h1>
          <div className="header-info">
            {selectedFile && (
              <span className="file-badge">
                当前文件: {selectedFile}
              </span>
            )}
            {sliceType === SliceType.INLINE && (
              <span className="slice-badge inline">
                Inline: {sliceValue}
              </span>
            )}
            {sliceType === SliceType.CROSSLINE && (
              <span className="slice-badge crossline">
                Crossline: {sliceValue}
              </span>
            )}
          </div>
        </header>

        <div className="plot-container">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {!seismicData && !isLoading && (
            <div className="empty-state">
              <div className="empty-icon">📊</div>
              <h2>欢迎使用地震波数据分析系统</h2>
              <p>请选择SEG-Y文件，建立索引后点击"加载数据"查看地震波形图</p>
              <div className="feature-list">
                <div className="feature-item">
                  <span className="feature-icon">📁</span>
                  <span>支持标准SEG-Y格式解析</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">🔍</span>
                  <span>按Inline/Crossline切片浏览</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">📈</span>
                  <span>高密度Wiggle变面积波形显示</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">🖱️</span>
                  <span>平滑拖拽漫游与缩放</span>
                </div>
              </div>
            </div>
          )}

          {isLoading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>正在加载地震数据...</p>
            </div>
          )}

          {seismicData && (
            <WigglePlot
              data={seismicData}
              metadata={metadata}
              width={1200}
              height={700}
              traceSpacing={3}
              amplitudeScale={amplitudeScale}
              onViewChange={handleViewChange}
              viewState={viewState}
            />
          )}
        </div>

        {seismicData && (
          <div className="data-info-bar">
            <div className="info-item">
              <span className="info-label">Inline范围:</span>
              <span className="info-value">{seismicData.inline_start} - {seismicData.inline_end}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Crossline范围:</span>
              <span className="info-value">{seismicData.crossline_start} - {seismicData.crossline_end}</span>
            </div>
            <div className="info-item">
              <span className="info-label">时间范围:</span>
              <span className="info-value">{seismicData.z_start.toFixed(0)} - {seismicData.z_end.toFixed(0)} ms</span>
            </div>
            <div className="info-item">
              <span className="info-label">数据维度:</span>
              <span className="info-value">{seismicData.trace_count} 道 × {seismicData.sample_count} 采样点</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
