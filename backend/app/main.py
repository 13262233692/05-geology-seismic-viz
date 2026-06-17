import os
import glob
import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .segy_parser import SegyParser
from .segy_reader import SegyReader
from .models import (
    SeismicMetadata, SliceRequest, SliceResponse,
    FileListResponse, FileInfo
)


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

app = FastAPI(
    title="地震波数据分析系统 API",
    description="石油地质勘测SEG-Y格式数据解析与可视化服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

segy_parser = SegyParser(data_dir=DATA_DIR)
segy_reader = SegyReader(segy_parser)


@app.on_event("startup")
async def startup_event():
    os.makedirs(DATA_DIR, exist_ok=True)


@app.on_event("shutdown")
async def shutdown_event():
    segy_parser.close()


@app.get("/api/health", tags=["系统"])
async def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}


@app.get("/api/files", response_model=FileListResponse, tags=["文件管理"])
async def list_files():
    segy_files = glob.glob(os.path.join(DATA_DIR, "*.sgy")) + \
                 glob.glob(os.path.join(DATA_DIR, "*.segy"))
    
    files_info = []
    for filepath in segy_files:
        filename = os.path.basename(filepath)
        stat = os.stat(filepath)
        index_path = os.path.join(DATA_DIR, f".{filename}.idx")
        has_index = os.path.exists(index_path)
        
        files_info.append(FileInfo(
            filename=filename,
            file_size=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            has_index=has_index
        ))
    
    return FileListResponse(
        files=files_info,
        total=len(files_info)
    )


@app.get("/api/metadata/{filename}", response_model=SeismicMetadata, tags=["数据查询"])
async def get_metadata(filename: str):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    try:
        return segy_parser.get_metadata(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/build-index/{filename}", tags=["数据管理"])
async def build_index(filename: str):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    try:
        index = segy_parser.build_index(filename)
        return {
            "status": "success",
            "filename": filename,
            "traces_count": index.traces_count,
            "inline_range": [index.min_inline, index.max_inline],
            "crossline_range": [index.min_crossline, index.max_crossline]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/slice", response_model=SliceResponse, tags=["数据查询"])
async def get_slice(request: SliceRequest):
    filepath = os.path.join(DATA_DIR, request.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {request.filename}")
    
    try:
        return segy_reader.get_slice(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/range", response_model=SliceResponse, tags=["数据查询"])
async def get_range(
    filename: str = Query(..., description="文件名"),
    min_inline: int = Query(..., description="最小Inline号"),
    max_inline: int = Query(..., description="最大Inline号"),
    min_crossline: int = Query(..., description="最小Crossline号"),
    max_crossline: int = Query(..., description="最大Crossline号"),
    z_min: Optional[float] = Query(None, description="最小深度/时间"),
    z_max: Optional[float] = Query(None, description="最大深度/时间"),
    max_traces: int = Query(800, description="最大返回道数"),
    max_samples: int = Query(500, description="最大返回采样点数"),
    downsample_method: str = Query("average", description="下采样方法")
):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    try:
        z_range = (z_min, z_max) if z_min is not None and z_max is not None else None
        return segy_reader.get_traces_by_range(
            filename=filename,
            inline_range=(min_inline, max_inline),
            crossline_range=(min_crossline, max_crossline),
            z_range=z_range,
            max_traces=max_traces,
            max_samples=max_samples,
            downsample_method=downsample_method
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
