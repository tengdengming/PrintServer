from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class PrintPaper(BaseModel):
    width_mm: int = Field(210)
    height_mm: int = Field(297)

class Layout(BaseModel):
    rows: int = Field(1, ge=1)
    cols: int = Field(1, ge=1)

class PrintRequest(BaseModel):
    path: str
    printer: Optional[str] = None
    copies: int = Field(1, ge=1)
    dpi: int = Field(300, ge=72)
    scale: float = Field(1.0, ge=0.1)
    margins_mm: List[int] = Field([10,10,10,10])
    layout: Layout = Layout()
    duplex: bool = False
    paper: PrintPaper = PrintPaper()
