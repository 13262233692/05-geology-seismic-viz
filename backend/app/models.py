from pydantic import BaseModel, Field
from typing import Optional, List, Tuple
from enum import Enum


class CoordinateType(str, Enum):
    TIME = "time"
    DEPTH = "depth"


class BinHeader(BaseModel):
    job_id: int = Field(description="作业标识")
    line_number: int = Field(description="测线号")
    sample_interval: int = Field(description="采样间隔(微秒)")
    samples_per_trace: int = Field(description="每道采样点数")
    data_sample_format: int = Field(description="数据采样格式代码")
    fold: int = Field(description="覆盖次数")
    sort_code: int = Field(description="排序代码")
    inline_bytes: int = Field(description="Inline号字节位置", default=189)
    crossline_bytes: int = Field(description="Crossline号字节位置", default=193)
    x_coordinate_bytes: int = Field(description="X坐标字节位置", default=181)
    y_coordinate_bytes: int = Field(description="Y坐标字节位置", default=185)


class TraceHeader(BaseModel):
    trace_sequence: int = Field(description="道序列号")
    inline: int = Field(description="Inline号")
    crossline: int = Field(description="Crossline号")
    x_coordinate: float = Field(description="X坐标")
    y_coordinate: float = Field(description="Y坐标")
    elevation: float = Field(description="高程")
    source_x: float = Field(description="震源X坐标")
    source_y: float = Field(description="震源Y坐标")
    receiver_x: float = Field(description="接收点X坐标")
    receiver_y: float = Field(description="接收点Y坐标")
    offset: float = Field(description="炮检距")
    sample_count: int = Field(description="采样点数")
    sample_interval: int = Field(description="采样间隔")


class SeismicMetadata(BaseModel):
    filename: str = Field(description="文件名")
    file_size: int = Field(description="文件大小(字节)")
    bin_header: BinHeader = Field(description="二进制卷头")
    min_inline: int = Field(description="最小Inline号")
    max_inline: int = Field(description="最大Inline号")
    min_crossline: int = Field(description="最小Crossline号")
    max_crossline: int = Field(description="最大Crossline号")
    inline_count: int = Field(description="Inline总数")
    crossline_count: int = Field(description="Crossline总数")
    traces_count: int = Field(description="总道数")
    samples_per_trace: int = Field(description="每道采样点数")
    sample_interval: float = Field(description="采样间隔(毫秒)")
    z_min: float = Field(description="最小时间/深度")
    z_max: float = Field(description="最大时间/深度")
    coordinate_type: CoordinateType = Field(description="坐标类型", default=CoordinateType.TIME)
    min_amplitude: float = Field(description="最小振幅值")
    max_amplitude: float = Field(description="最大振幅值")


class SliceRequest(BaseModel):
    filename: str = Field(description="文件名")
    slice_type: str = Field(description="切片类型: inline, crossline, timeslice, depthslice")
    slice_value: int = Field(description="切片值")
    inline_range: Optional[Tuple[int, int]] = Field(None, description="Inline范围(min, max)")
    crossline_range: Optional[Tuple[int, int]] = Field(None, description="Crossline范围(min, max)")
    z_range: Optional[Tuple[float, float]] = Field(None, description="深度/时间范围(min, max)")
    max_samples: Optional[int] = Field(500, description="最大采样点数(用于下采样)")
    max_traces: Optional[int] = Field(800, description="最大道数(用于下采样)")
    downsample_method: Optional[str] = Field("average", description="下采样方法: average, max, min, decimate")


class SliceResponse(BaseModel):
    data: List[List[float]] = Field(description="二维振幅数组 [traces][samples]")
    inline_start: int = Field(description="起始Inline")
    inline_end: int = Field(description="结束Inline")
    inline_step: int = Field(description="Inline步长")
    crossline_start: int = Field(description="起始Crossline")
    crossline_end: int = Field(description="结束Crossline")
    crossline_step: int = Field(description="Crossline步长")
    z_start: float = Field(description="起始深度/时间")
    z_end: float = Field(description="结束深度/时间")
    z_step: float = Field(description="深度/时间步长")
    trace_count: int = Field(description="实际返回道数")
    sample_count: int = Field(description="实际返回采样点数")
    min_amplitude: float = Field(description="返回数据最小振幅")
    max_amplitude: float = Field(description="返回数据最大振幅")
    coordinate_type: CoordinateType = Field(description="坐标类型")


class FileInfo(BaseModel):
    filename: str = Field(description="文件名")
    file_size: int = Field(description="文件大小(字节)")
    created_at: str = Field(description="创建时间")
    modified_at: str = Field(description="修改时间")
    has_index: bool = Field(description="是否已建立索引")


class FileListResponse(BaseModel):
    files: List[FileInfo] = Field(description="文件列表")
    total: int = Field(description="文件总数")
