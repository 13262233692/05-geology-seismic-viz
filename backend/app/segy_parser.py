import os
import struct
import numpy as np
from typing import Dict, List, Tuple, Optional, BinaryIO
from dataclasses import dataclass, field
import pickle
import hashlib

from .models import BinHeader, TraceHeader, SeismicMetadata, CoordinateType


TEXT_HEADER_SIZE = 3200
BINARY_HEADER_SIZE = 400
TRACE_HEADER_SIZE = 240


@dataclass
class SegyIndex:
    filename: str
    file_hash: str
    file_size: int
    traces_count: int
    samples_per_trace: int
    sample_interval: float
    inline_to_offset: Dict[int, List[int]] = field(default_factory=dict)
    crossline_to_offset: Dict[int, List[int]] = field(default_factory=dict)
    inline_crossline_to_offset: Dict[Tuple[int, int], int] = field(default_factory=dict)
    min_inline: int = 0
    max_inline: int = 0
    min_crossline: int = 0
    max_crossline: int = 0
    min_amplitude: float = 0.0
    max_amplitude: float = 0.0
    trace_headers: List[TraceHeader] = field(default_factory=list)
    built: bool = False


class SegyParser:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self._index_cache: Dict[str, SegyIndex] = {}
        self._file_cache: Dict[str, BinaryIO] = {}

    def _get_file_path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    def _get_index_path(self, filename: str) -> str:
        return os.path.join(self.data_dir, f".{filename}.idx")

    def _compute_file_hash(self, filepath: str) -> str:
        hasher = hashlib.md5()
        file_size = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            hasher.update(f.read(65536))
            if file_size > 65536:
                f.seek(file_size - 65536)
                hasher.update(f.read(65536))
        return hasher.hexdigest() + f"_{file_size}"

    def _load_index(self, filename: str) -> Optional[SegyIndex]:
        index_path = self._get_index_path(filename)
        if not os.path.exists(index_path):
            return None
        try:
            with open(index_path, 'rb') as f:
                index = pickle.load(f)
                file_hash = self._compute_file_hash(self._get_file_path(filename))
                if index.file_hash == file_hash:
                    return index
        except Exception:
            pass
        return None

    def _save_index(self, index: SegyIndex) -> None:
        index_path = self._get_index_path(index.filename)
        try:
            with open(index_path, 'wb') as f:
                pickle.dump(index, f)
        except Exception:
            pass

    def _open_file(self, filename: str) -> BinaryIO:
        if filename not in self._file_cache:
            filepath = self._get_file_path(filename)
            self._file_cache[filename] = open(filepath, 'rb')
        return self._file_cache[filename]

    def _read_int(self, f: BinaryIO, offset: int, size: int = 4) -> int:
        f.seek(offset)
        if size == 2:
            return struct.unpack('>h', f.read(2))[0]
        elif size == 4:
            return struct.unpack('>i', f.read(4))[0]
        return 0

    def _read_uint(self, f: BinaryIO, offset: int, size: int = 4) -> int:
        f.seek(offset)
        if size == 2:
            return struct.unpack('>H', f.read(2))[0]
        elif size == 4:
            return struct.unpack('>I', f.read(4))[0]
        return 0

    def _read_float(self, f: BinaryIO, offset: int) -> float:
        f.seek(offset)
        return struct.unpack('>f', f.read(4))[0]

    def parse_binary_header(self, f: BinaryIO) -> BinHeader:
        base_offset = TEXT_HEADER_SIZE
        
        return BinHeader(
            job_id=self._read_int(f, base_offset + 0),
            line_number=self._read_int(f, base_offset + 4),
            sample_interval=self._read_uint(f, base_offset + 16, 2),
            samples_per_trace=self._read_uint(f, base_offset + 20, 2),
            data_sample_format=self._read_uint(f, base_offset + 24, 2),
            fold=self._read_uint(f, base_offset + 32, 2),
            sort_code=self._read_uint(f, base_offset + 36, 2),
            inline_bytes=189,
            crossline_bytes=193,
            x_coordinate_bytes=181,
            y_coordinate_bytes=185,
        )

    def parse_trace_header(self, f: BinaryIO, trace_offset: int, 
                          inline_bytes: int = 189, crossline_bytes: int = 193,
                          x_bytes: int = 181, y_bytes: int = 185) -> TraceHeader:
        base_offset = trace_offset
        
        return TraceHeader(
            trace_sequence=self._read_int(f, base_offset + 0),
            inline=self._read_int(f, base_offset + inline_bytes),
            crossline=self._read_int(f, base_offset + crossline_bytes),
            x_coordinate=float(self._read_int(f, base_offset + x_bytes)),
            y_coordinate=float(self._read_int(f, base_offset + y_bytes)),
            elevation=float(self._read_int(f, base_offset + 40)),
            source_x=float(self._read_int(f, base_offset + 72)),
            source_y=float(self._read_int(f, base_offset + 76)),
            receiver_x=float(self._read_int(f, base_offset + 80)),
            receiver_y=float(self._read_int(f, base_offset + 84)),
            offset=float(self._read_int(f, base_offset + 36)),
            sample_count=self._read_uint(f, base_offset + 114, 2),
            sample_interval=self._read_uint(f, base_offset + 116, 2),
        )

    def read_trace_samples(self, f: BinaryIO, trace_offset: int, 
                          samples_per_trace: int, format_code: int,
                          start_sample: int = 0, end_sample: Optional[int] = None) -> np.ndarray:
        if end_sample is None:
            end_sample = samples_per_trace
        
        samples_to_read = end_sample - start_sample
        data_offset = trace_offset + TRACE_HEADER_SIZE + start_sample * 4
        
        f.seek(data_offset)
        raw_data = f.read(samples_to_read * 4)
        
        if format_code == 1:
            dtype = '>f4'
        elif format_code == 2:
            dtype = '>i4'
        elif format_code == 3:
            dtype = '>i2'
        elif format_code == 5:
            dtype = '<f4'
        else:
            dtype = '>f4'
        
        samples = np.frombuffer(raw_data, dtype=dtype)
        return samples.astype(np.float32)

    def build_index(self, filename: str, progress_callback=None) -> SegyIndex:
        cached = self._load_index(filename)
        if cached is not None and cached.built:
            self._index_cache[filename] = cached
            return cached

        filepath = self._get_file_path(filename)
        file_size = os.path.getsize(filepath)
        file_hash = self._compute_file_hash(filepath)
        
        index = SegyIndex(
            filename=filename,
            file_hash=file_hash,
            file_size=file_size,
            traces_count=0,
            samples_per_trace=0,
            sample_interval=0.0,
        )

        with open(filepath, 'rb') as f:
            bin_header = self.parse_binary_header(f)
            index.samples_per_trace = bin_header.samples_per_trace
            index.sample_interval = bin_header.sample_interval / 1000.0
            
            trace_data_size = TRACE_HEADER_SIZE + bin_header.samples_per_trace * 4
            first_trace_offset = TEXT_HEADER_SIZE + BINARY_HEADER_SIZE
            
            estimated_traces = (file_size - first_trace_offset) // trace_data_size
            index.traces_count = estimated_traces
            
            min_inline = float('inf')
            max_inline = float('-inf')
            min_crossline = float('inf')
            max_crossline = float('-inf')
            min_amp = float('inf')
            max_amp = float('-inf')
            
            for i in range(estimated_traces):
                trace_offset = first_trace_offset + i * trace_data_size
                
                if trace_offset + TRACE_HEADER_SIZE > file_size:
                    index.traces_count = i
                    break
                
                trace_header = self.parse_trace_header(
                    f, trace_offset,
                    bin_header.inline_bytes,
                    bin_header.crossline_bytes,
                    bin_header.x_coordinate_bytes,
                    bin_header.y_coordinate_bytes
                )
                
                inline = trace_header.inline
                crossline = trace_header.crossline
                
                index.trace_headers.append(trace_header)
                index.inline_crossline_to_offset[(inline, crossline)] = trace_offset
                
                if inline not in index.inline_to_offset:
                    index.inline_to_offset[inline] = []
                index.inline_to_offset[inline].append(trace_offset)
                
                if crossline not in index.crossline_to_offset:
                    index.crossline_to_offset[crossline] = []
                index.crossline_to_offset[crossline].append(trace_offset)
                
                min_inline = min(min_inline, inline)
                max_inline = max(max_inline, inline)
                min_crossline = min(min_crossline, crossline)
                max_crossline = max(max_crossline, crossline)
                
                if i % 1000 == 0:
                    samples = self.read_trace_samples(
                        f, trace_offset, 
                        bin_header.samples_per_trace,
                        bin_header.data_sample_format
                    )
                    if len(samples) > 0:
                        min_amp = min(min_amp, float(np.min(samples)))
                        max_amp = max(max_amp, float(np.max(samples)))
                    
                    if progress_callback and i % 5000 == 0:
                        progress_callback(i, estimated_traces)
            
            index.min_inline = min_inline if min_inline != float('inf') else 0
            index.max_inline = max_inline if max_inline != float('-inf') else 0
            index.min_crossline = min_crossline if min_crossline != float('inf') else 0
            index.max_crossline = max_crossline if max_crossline != float('-inf') else 0
            index.min_amplitude = min_amp if min_amp != float('inf') else -1.0
            index.max_amplitude = max_amp if max_amp != float('-inf') else 1.0
            index.built = True
            
            inline_keys = sorted(index.inline_to_offset.keys())
            crossline_keys = sorted(index.crossline_to_offset.keys())
            for inline in inline_keys:
                index.inline_to_offset[inline].sort()
            for crossline in crossline_keys:
                index.crossline_to_offset[crossline].sort()

        self._save_index(index)
        self._index_cache[filename] = index
        
        return index

    def get_metadata(self, filename: str) -> SeismicMetadata:
        index = self.build_index(filename)
        f = self._open_file(filename)
        bin_header = self.parse_binary_header(f)
        
        inline_count = len(index.inline_to_offset)
        crossline_count = len(index.crossline_to_offset)
        
        return SeismicMetadata(
            filename=filename,
            file_size=index.file_size,
            bin_header=bin_header,
            min_inline=index.min_inline,
            max_inline=index.max_inline,
            min_crossline=index.min_crossline,
            max_crossline=index.max_crossline,
            inline_count=inline_count,
            crossline_count=crossline_count,
            traces_count=index.traces_count,
            samples_per_trace=index.samples_per_trace,
            sample_interval=index.sample_interval,
            z_min=0.0,
            z_max=index.samples_per_trace * index.sample_interval,
            coordinate_type=CoordinateType.TIME,
            min_amplitude=index.min_amplitude,
            max_amplitude=index.max_amplitude,
        )

    def close(self):
        for f in self._file_cache.values():
            f.close()
        self._file_cache.clear()
        self._index_cache.clear()
