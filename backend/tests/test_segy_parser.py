import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.segy_parser import SegyParser
from app.segy_reader import SegyReader, Downsampler
from app.mock_segy_generator import create_mock_segy


@pytest.fixture(scope="module")
def test_segy_file():
    filename = "test_parser.sgy"
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    
    filepath = create_mock_segy(
        filename,
        inline_count=10,
        crossline_count=20,
        samples_per_trace=500,
        sample_interval=2000,
        data_dir=data_dir
    )
    
    yield filename
    
    if os.path.exists(filepath):
        os.remove(filepath)
    index_path = os.path.join(data_dir, f".{filename}.idx")
    if os.path.exists(index_path):
        os.remove(index_path)


@pytest.fixture(scope="module")
def parser():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    parser = SegyParser(data_dir=data_dir)
    yield parser
    parser.close()


@pytest.fixture(scope="module")
def reader(parser):
    return SegyReader(parser)


class TestSegyParser:
    def test_build_index(self, parser, test_segy_file):
        index = parser.build_index(test_segy_file)
        
        assert index is not None
        assert index.built is True
        assert index.traces_count == 200
        assert index.samples_per_trace == 500
        assert index.min_inline == 100
        assert index.max_inline == 109
        assert index.min_crossline == 1000
        assert index.max_crossline == 1019
        assert len(index.inline_to_offset) == 10
        assert len(index.crossline_to_offset) == 20
        assert len(index.inline_crossline_to_offset) == 200

    def test_get_metadata(self, parser, test_segy_file):
        metadata = parser.get_metadata(test_segy_file)
        
        assert metadata is not None
        assert metadata.filename == test_segy_file
        assert metadata.traces_count == 200
        assert metadata.samples_per_trace == 500
        assert metadata.sample_interval == 2.0
        assert metadata.z_max == 1000.0
        assert metadata.inline_count == 10
        assert metadata.crossline_count == 20

    def test_parse_binary_header(self, parser, test_segy_file):
        parser.build_index(test_segy_file)
        f = parser._open_file(test_segy_file)
        bin_header = parser.parse_binary_header(f)
        
        assert bin_header is not None
        assert bin_header.samples_per_trace == 500
        assert bin_header.sample_interval == 2000
        assert bin_header.data_sample_format == 1

    def test_read_trace_samples(self, parser, test_segy_file):
        index = parser.build_index(test_segy_file)
        f = parser._open_file(test_segy_file)
        
        first_offset = index.inline_to_offset[100][0]
        metadata = parser.get_metadata(test_segy_file)
        
        samples = parser.read_trace_samples(
            f, first_offset,
            index.samples_per_trace,
            metadata.bin_header.data_sample_format
        )
        
        assert len(samples) == 500
        assert samples.dtype == np.float32
        assert np.max(np.abs(samples)) > 0

    def test_read_partial_samples(self, parser, test_segy_file):
        index = parser.build_index(test_segy_file)
        f = parser._open_file(test_segy_file)
        
        first_offset = index.inline_to_offset[100][0]
        metadata = parser.get_metadata(test_segy_file)
        
        samples = parser.read_trace_samples(
            f, first_offset,
            index.samples_per_trace,
            metadata.bin_header.data_sample_format,
            start_sample=100,
            end_sample=200
        )
        
        assert len(samples) == 100


class TestDownsampler:
    def test_downsample_trace_average(self):
        trace = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
        result = Downsampler.downsample_trace(trace, 4, 'average')
        
        assert len(result) == 4
        assert np.allclose(result, [1.5, 3.5, 5.5, 7.5])

    def test_downsample_trace_max(self):
        trace = np.array([1.0, 3.0, 2.0, 4.0, 6.0, 5.0, 8.0, 7.0], dtype=np.float32)
        result = Downsampler.downsample_trace(trace, 4, 'max')
        
        assert len(result) == 4
        assert np.allclose(result, [3.0, 4.0, 6.0, 8.0])

    def test_downsample_trace_decimate(self):
        trace = np.arange(100, dtype=np.float32)
        result = Downsampler.downsample_trace(trace, 10, 'decimate')
        
        assert len(result) == 10
        assert result[0] == 0
        assert result[9] == 90

    def test_downsample_traces(self):
        traces = [
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([3.0, 4.0, 5.0], dtype=np.float32),
            np.array([5.0, 6.0, 7.0], dtype=np.float32),
            np.array([7.0, 8.0, 9.0], dtype=np.float32),
        ]
        
        result = Downsampler.downsample_traces(traces, 2, 'average')
        
        assert len(result) == 2
        assert len(result[0]) == 3
        assert np.allclose(result[0], [2.0, 3.0, 4.0])
        assert np.allclose(result[1], [6.0, 7.0, 8.0])


class TestSegyReader:
    def test_get_inline_slice(self, reader, test_segy_file):
        from app.models import SliceRequest
        
        request = SliceRequest(
            filename=test_segy_file,
            slice_type='inline',
            slice_value=105,
            max_traces=20,
            max_samples=250,
            downsample_method='average'
        )
        
        response = reader.get_slice(request)
        
        assert response is not None
        assert response.trace_count == 20
        assert response.sample_count == 250
        assert response.inline_start == 105
        assert response.inline_end == 105
        assert len(response.data) == 20
        assert len(response.data[0]) == 250

    def test_get_crossline_slice(self, reader, test_segy_file):
        from app.models import SliceRequest
        
        request = SliceRequest(
            filename=test_segy_file,
            slice_type='crossline',
            slice_value=1010,
            max_traces=10,
            max_samples=250,
            downsample_method='average'
        )
        
        response = reader.get_slice(request)
        
        assert response is not None
        assert response.trace_count == 10
        assert response.sample_count == 250
        assert response.crossline_start == 1010
        assert response.crossline_end == 1010

    def test_get_traces_by_range(self, reader, test_segy_file):
        response = reader.get_traces_by_range(
            filename=test_segy_file,
            inline_range=(102, 105),
            crossline_range=(1005, 1015),
            max_traces=40,
            max_samples=200,
            downsample_method='average'
        )
        
        assert response is not None
        assert response.trace_count > 0
        assert response.sample_count == 200
        assert response.inline_start == 102
        assert response.inline_end == 105
        assert response.crossline_start == 1005
        assert response.crossline_end == 1015

    def test_slice_with_z_range(self, reader, test_segy_file):
        from app.models import SliceRequest
        
        request = SliceRequest(
            filename=test_segy_file,
            slice_type='inline',
            slice_value=105,
            z_range=(200.0, 600.0),
            max_traces=20,
            max_samples=200,
            downsample_method='average'
        )
        
        response = reader.get_slice(request)
        
        assert response is not None
        assert response.z_start >= 200.0
        assert response.z_end <= 600.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
