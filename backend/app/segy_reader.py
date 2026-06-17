import numpy as np
from typing import List, Tuple, Optional, Dict
import time

from .segy_parser import SegyParser, SegyIndex
from .models import SliceRequest, SliceResponse, CoordinateType, SeismicMetadata


class Downsampler:
    @staticmethod
    def downsample_trace(trace: np.ndarray, target_samples: int, 
                        method: str = 'average') -> np.ndarray:
        if len(trace) <= target_samples:
            return trace
        
        if method == 'decimate':
            step = len(trace) / target_samples
            indices = np.arange(0, len(trace), step).astype(int)[:target_samples]
            return trace[indices]
        
        elif method == 'max':
            return Downsampler._aggregate_downsample(trace, target_samples, np.max)
        
        elif method == 'min':
            return Downsampler._aggregate_downsample(trace, target_samples, np.min)
        
        elif method == 'average':
            return Downsampler._aggregate_downsample(trace, target_samples, np.mean)
        
        else:
            return Downsampler._aggregate_downsample(trace, target_samples, np.mean)
    
    @staticmethod
    def _aggregate_downsample(trace: np.ndarray, target_samples: int, 
                              agg_func) -> np.ndarray:
        n = len(trace)
        result = np.zeros(target_samples, dtype=np.float32)
        bin_size = n / target_samples
        
        for i in range(target_samples):
            start = int(i * bin_size)
            end = int((i + 1) * bin_size)
            if start == end:
                end = start + 1
            end = min(end, n)
            result[i] = agg_func(trace[start:end])
        
        return result
    
    @staticmethod
    def downsample_traces(traces: List[np.ndarray], target_traces: int,
                         method: str = 'average') -> List[np.ndarray]:
        if len(traces) <= target_traces:
            return traces
        
        result = []
        n = len(traces)
        bin_size = n / target_traces
        
        for i in range(target_traces):
            start = int(i * bin_size)
            end = int((i + 1) * bin_size)
            if start == end:
                end = start + 1
            end = min(end, n)
            
            if method == 'decimate':
                result.append(traces[start])
            elif method == 'average':
                stacked = np.stack(traces[start:end])
                result.append(np.mean(stacked, axis=0))
            elif method == 'max':
                stacked = np.stack(traces[start:end])
                result.append(np.max(stacked, axis=0))
            elif method == 'min':
                stacked = np.stack(traces[start:end])
                result.append(np.min(stacked, axis=0))
            else:
                stacked = np.stack(traces[start:end])
                result.append(np.mean(stacked, axis=0))
        
        return result


class SegyReader:
    def __init__(self, parser: SegyParser):
        self.parser = parser
        self.downsampler = Downsampler()
    
    def _get_trace_offsets_for_inline(self, index: SegyIndex, 
                                      inline_value: int,
                                      crossline_range: Optional[Tuple[int, int]] = None
                                      ) -> List[int]:
        if inline_value not in index.inline_to_offset:
            return []
        
        offsets = index.inline_to_offset[inline_value]
        
        if crossline_range is None:
            return offsets
        
        min_xl, max_xl = crossline_range
        filtered_offsets = []
        
        for offset in offsets:
            header = next((h for h in index.trace_headers 
                         if index.inline_crossline_to_offset.get(
                             (inline_value, h.crossline)) == offset), None)
            if header and min_xl <= header.crossline <= max_xl:
                filtered_offsets.append(offset)
        
        return filtered_offsets
    
    def _get_trace_offsets_for_crossline(self, index: SegyIndex,
                                         crossline_value: int,
                                         inline_range: Optional[Tuple[int, int]] = None
                                         ) -> List[int]:
        if crossline_value not in index.crossline_to_offset:
            return []
        
        offsets = index.crossline_to_offset[crossline_value]
        
        if inline_range is None:
            return offsets
        
        min_il, max_il = inline_range
        filtered_offsets = []
        
        for offset in offsets:
            header = next((h for h in index.trace_headers
                         if index.inline_crossline_to_offset.get(
                             (h.inline, crossline_value)) == offset), None)
            if header and min_il <= header.inline <= max_il:
                filtered_offsets.append(offset)
        
        return filtered_offsets
    
    def _get_sample_range(self, z_range: Optional[Tuple[float, float]],
                         sample_interval: float,
                         samples_per_trace: int) -> Tuple[int, int]:
        if z_range is None:
            return (0, samples_per_trace)
        
        z_min, z_max = z_range
        start_sample = max(0, int(z_min / sample_interval))
        end_sample = min(samples_per_trace, int(z_max / sample_interval))
        
        if end_sample <= start_sample:
            end_sample = min(start_sample + 1, samples_per_trace)
        
        return (start_sample, end_sample)
    
    def _downsample_traces(self, traces_data: List[np.ndarray],
                           target_traces: int,
                           target_samples: int,
                           method: str = 'average'
                           ) -> Tuple[List[np.ndarray], int, int]:
        current_traces = len(traces_data)
        current_samples = len(traces_data[0]) if traces_data else 0
        
        trace_step = 1
        sample_step = 1
        
        if current_traces > target_traces:
            trace_step = current_traces / target_traces
            traces_data = self.downsampler.downsample_traces(
                traces_data, target_traces, method)
        
        if current_samples > target_samples:
            sample_step = current_samples / target_samples
            traces_data = [
                self.downsampler.downsample_trace(trace, target_samples, method)
                for trace in traces_data
            ]
        
        return traces_data, int(trace_step), int(sample_step)
    
    def get_slice(self, request: SliceRequest) -> SliceResponse:
        index = self.parser.build_index(request.filename)
        f = self.parser._open_file(request.filename)
        metadata = self.parser.get_metadata(request.filename)
        bin_header = metadata.bin_header
        
        if request.slice_type == 'inline':
            trace_offsets = self._get_trace_offsets_for_inline(
                index, request.slice_value, request.crossline_range)
            axis_value = request.slice_value
            
            crossline_values = []
            for offset in trace_offsets:
                hdr = next((h for h in index.trace_headers
                          if index.inline_crossline_to_offset.get(
                              (axis_value, h.crossline)) == offset), None)
                if hdr:
                    crossline_values.append(hdr.crossline)
            
        elif request.slice_type == 'crossline':
            trace_offsets = self._get_trace_offsets_for_crossline(
                index, request.slice_value, request.inline_range)
            axis_value = request.slice_value
            
            inline_values = []
            for offset in trace_offsets:
                hdr = next((h for h in index.trace_headers
                          if index.inline_crossline_to_offset.get(
                              (h.inline, axis_value)) == offset), None)
                if hdr:
                    inline_values.append(hdr.inline)
        
        else:
            raise ValueError(f"Unsupported slice type: {request.slice_type}")
        
        if not trace_offsets:
            raise ValueError(f"No traces found for {request.slice_type}={request.slice_value}")
        
        start_sample, end_sample = self._get_sample_range(
            request.z_range, index.sample_interval, index.samples_per_trace)
        
        traces_data = []
        min_amp = float('inf')
        max_amp = float('-inf')
        
        for offset in trace_offsets:
            samples = self.parser.read_trace_samples(
                f, offset, index.samples_per_trace,
                bin_header.data_sample_format,
                start_sample, end_sample
            )
            traces_data.append(samples)
            min_amp = min(min_amp, float(np.min(samples)))
            max_amp = max(max_amp, float(np.max(samples)))
        
        target_traces = request.max_traces or 800
        target_samples = request.max_samples or 500
        
        traces_data, trace_step, sample_step = self._downsample_traces(
            traces_data, target_traces, target_samples,
            request.downsample_method or 'average'
        )
        
        data_list = [trace.tolist() for trace in traces_data]
        
        z_start = start_sample * index.sample_interval
        z_end = end_sample * index.sample_interval
        z_step = index.sample_interval * sample_step
        
        if request.slice_type == 'inline':
            if crossline_values:
                crossline_start = min(crossline_values)
                crossline_end = max(crossline_values)
            else:
                crossline_start = index.min_crossline
                crossline_end = index.max_crossline
            
            return SliceResponse(
                data=data_list,
                inline_start=axis_value,
                inline_end=axis_value,
                inline_step=1,
                crossline_start=crossline_start,
                crossline_end=crossline_end,
                crossline_step=trace_step,
                z_start=z_start,
                z_end=z_end,
                z_step=z_step,
                trace_count=len(traces_data),
                sample_count=len(traces_data[0]) if traces_data else 0,
                min_amplitude=min_amp,
                max_amplitude=max_amp,
                coordinate_type=CoordinateType.TIME,
            )
        
        else:
            if inline_values:
                inline_start = min(inline_values)
                inline_end = max(inline_values)
            else:
                inline_start = index.min_inline
                inline_end = index.max_inline
            
            return SliceResponse(
                data=data_list,
                inline_start=inline_start,
                inline_end=inline_end,
                inline_step=trace_step,
                crossline_start=axis_value,
                crossline_end=axis_value,
                crossline_step=1,
                z_start=z_start,
                z_end=z_end,
                z_step=z_step,
                trace_count=len(traces_data),
                sample_count=len(traces_data[0]) if traces_data else 0,
                min_amplitude=min_amp,
                max_amplitude=max_amp,
                coordinate_type=CoordinateType.TIME,
            )
    
    def get_traces_by_range(self, filename: str,
                           inline_range: Tuple[int, int],
                           crossline_range: Tuple[int, int],
                           z_range: Optional[Tuple[float, float]] = None,
                           max_traces: int = 800,
                           max_samples: int = 500,
                           downsample_method: str = 'average'
                           ) -> SliceResponse:
        index = self.parser.build_index(filename)
        f = self.parser._open_file(filename)
        metadata = self.parser.get_metadata(filename)
        bin_header = metadata.bin_header
        
        min_il, max_il = inline_range
        min_xl, max_xl = crossline_range
        
        inline_values = sorted([il for il in index.inline_to_offset.keys()
                               if min_il <= il <= max_il])
        
        trace_offsets = []
        for il in inline_values:
            offsets = index.inline_to_offset[il]
            for offset in offsets:
                hdr = next((h for h in index.trace_headers
                          if index.inline_crossline_to_offset.get(
                              (il, h.crossline)) == offset), None)
                if hdr and min_xl <= hdr.crossline <= max_xl:
                    trace_offsets.append(offset)
        
        if not trace_offsets:
            raise ValueError(f"No traces found in the specified range")
        
        start_sample, end_sample = self._get_sample_range(
            z_range, index.sample_interval, index.samples_per_trace)
        
        traces_data = []
        min_amp = float('inf')
        max_amp = float('-inf')
        
        for offset in trace_offsets:
            samples = self.parser.read_trace_samples(
                f, offset, index.samples_per_trace,
                bin_header.data_sample_format,
                start_sample, end_sample
            )
            traces_data.append(samples)
            min_amp = min(min_amp, float(np.min(samples)))
            max_amp = max(max_amp, float(np.max(samples)))
        
        traces_data, trace_step, sample_step = self._downsample_traces(
            traces_data, max_traces, max_samples, downsample_method
        )
        
        data_list = [trace.tolist() for trace in traces_data]
        
        z_start = start_sample * index.sample_interval
        z_end = end_sample * index.sample_interval
        z_step = index.sample_interval * sample_step
        
        return SliceResponse(
            data=data_list,
            inline_start=min_il,
            inline_end=max_il,
            inline_step=trace_step,
            crossline_start=min_xl,
            crossline_end=max_xl,
            crossline_step=trace_step,
            z_start=z_start,
            z_end=z_end,
            z_step=z_step,
            trace_count=len(traces_data),
            sample_count=len(traces_data[0]) if traces_data else 0,
            min_amplitude=min_amp,
            max_amplitude=max_amp,
            coordinate_type=CoordinateType.TIME,
        )
