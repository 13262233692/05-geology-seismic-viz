import os
import struct
import numpy as np
from typing import Optional


TEXT_HEADER_SIZE = 3200
BINARY_HEADER_SIZE = 400
TRACE_HEADER_SIZE = 240


def create_mock_segy(filename: str, 
                     inline_count: int = 50,
                     crossline_count: int = 100,
                     samples_per_trace: int = 1000,
                     sample_interval: int = 2000,
                     data_dir: Optional[str] = None) -> str:
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, filename)
    
    total_traces = inline_count * crossline_count
    
    with open(filepath, 'wb') as f:
        text_header = b"C " * 1600
        f.write(text_header)
        
        binary_header = bytearray(BINARY_HEADER_SIZE)
        
        struct.pack_into('>i', binary_header, 0, 1001)
        struct.pack_into('>i', binary_header, 4, 2002)
        struct.pack_into('>H', binary_header, 16, sample_interval)
        struct.pack_into('>H', binary_header, 20, samples_per_trace)
        struct.pack_into('>H', binary_header, 24, 1)
        struct.pack_into('>H', binary_header, 32, 30)
        struct.pack_into('>H', binary_header, 36, 4)
        
        f.write(binary_header)
        
        rng = np.random.RandomState(42)
        
        for trace_idx in range(total_traces):
            inline = trace_idx // crossline_count + 100
            crossline = trace_idx % crossline_count + 1000
            
            trace_header = bytearray(TRACE_HEADER_SIZE)
            
            struct.pack_into('>i', trace_header, 0, trace_idx + 1)
            struct.pack_into('>i', trace_header, 8, inline)
            struct.pack_into('>i', trace_header, 12, crossline)
            struct.pack_into('>i', trace_header, 36, trace_idx % 1000)
            struct.pack_into('>i', trace_header, 40, 100)
            struct.pack_into('>i', trace_header, 72, inline * 100)
            struct.pack_into('>i', trace_header, 76, crossline * 100)
            struct.pack_into('>i', trace_header, 80, inline * 100 + 50)
            struct.pack_into('>i', trace_header, 84, crossline * 100 + 50)
            struct.pack_into('>i', trace_header, 181, inline * 100)
            struct.pack_into('>i', trace_header, 185, crossline * 100)
            struct.pack_into('>i', trace_header, 189, inline)
            struct.pack_into('>i', trace_header, 193, crossline)
            struct.pack_into('>H', trace_header, 114, samples_per_trace)
            struct.pack_into('>H', trace_header, 116, sample_interval)
            
            f.write(trace_header)
            
            samples = _generate_seismic_trace(samples_per_trace, inline, crossline, rng)
            f.write(samples.astype('>f4').tobytes())
    
    return filepath


def _generate_seismic_trace(n_samples: int, inline: int, crossline: int, rng) -> np.ndarray:
    t = np.arange(n_samples)
    
    signal = np.zeros(n_samples)
    
    n_reflectors = rng.randint(5, 15)
    for _ in range(n_reflectors):
        depth = rng.randint(50, n_samples - 100)
        amplitude = rng.uniform(0.3, 1.5)
        freq = rng.uniform(20, 60)
        phase = rng.uniform(0, 2 * np.pi)
        
        wavelet = _ricker_wavelet(n_samples, depth, freq, 1000)
        signal += amplitude * wavelet * np.cos(phase)
    
    noise_level = 0.15
    noise = rng.normal(0, noise_level, n_samples)
    
    decay = np.exp(-t / (n_samples * 0.6))
    signal = signal * decay + noise
    
    signal = signal / np.max(np.abs(signal)) if np.max(np.abs(signal)) > 0 else signal
    
    return signal.astype(np.float32)


def _ricker_wavelet(n_samples: int, center: int, freq: float, dt: float) -> np.ndarray:
    t = (np.arange(n_samples) - center) * dt / 1000000.0
    tau = 1.0 / freq
    sigma = tau / 3.0
    
    envelope = np.exp(-(t ** 2) / (2 * sigma ** 2))
    derivative = -2 * t / (2 * sigma ** 2) * envelope
    wavelet = (1 - 2 * (np.pi ** 2) * (freq ** 2) * (t ** 2)) * envelope
    
    return wavelet


if __name__ == "__main__":
    print("Creating mock SEG-Y file...")
    filepath = create_mock_segy(
        "test_data.sgy",
        inline_count=30,
        crossline_count=60,
        samples_per_trace=800,
        sample_interval=2000
    )
    print(f"Created: {filepath}")
    print(f"File size: {os.path.getsize(filepath) / 1024 / 1024:.2f} MB")
