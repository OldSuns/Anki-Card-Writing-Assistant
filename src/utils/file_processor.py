"""
文件处理工具模块
支持多种文件格式的读取和解析
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import mimetypes

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

@dataclass
class FileInfo:
    """文件信息"""
    filename: str
    file_path: str
    file_size: int
    file_type: str
    mime_type: str
    encoding: str = 'utf-8'
    content_preview: str = ''
    total_lines: int = 0
    total_words: int = 0

@dataclass
class ProcessedContent:
    """处理后的内容"""
    original_file: FileInfo
    sections: List[str]
    metadata: Dict[str, Any]

class FileProcessor:
    """文件处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_extensions = {
            '.txt': self._read_text_file,
            '.md': self._read_markdown_file,
            '.docx': self._read_docx_file,
            '.pdf': self._read_pdf_file,
            '.csv': self._read_csv_file,
            '.xlsx': self._read_excel_file,
            '.xls': self._read_excel_file
        }
    
    def is_supported_file(self, file_path: str) -> bool:
        """检查文件是否支持"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions
    
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return list(self.supported_extensions.keys())
    
    def get_file_info(self, file_path: str) -> FileInfo:
        """获取文件信息"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件大小
        file_size = path.stat().st_size
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or 'application/octet-stream'
        
        # 获取文件类型
        file_type = path.suffix.lower()
        
        # 读取内容预览
        content_preview = self._get_content_preview(file_path)
        
        # 统计行数和字数
        total_lines, total_words = self._count_lines_and_words(file_path)
        
        return FileInfo(
            filename=path.name,
            file_path=str(path),
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            content_preview=content_preview,
            total_lines=total_lines,
            total_words=total_words
        )
    
    def process_file(self, file_path: str) -> ProcessedContent:
        """处理文件并返回结构化内容"""
        file_info = self.get_file_info(file_path)
        
        # 根据文件类型选择处理方法
        ext = file_info.file_type
        if ext not in self.supported_extensions:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        # 调用对应的处理方法
        sections = self.supported_extensions[ext](file_path)
        
        # 构建元数据
        metadata = {
            'file_info': file_info,
            'section_count': len(sections),
            'processing_method': f'{ext}_processor'
        }
        
        return ProcessedContent(
            original_file=file_info,
            sections=sections,
            metadata=metadata
        )
    
    def _get_content_preview(self, file_path: str, max_length: int = 500) -> str:
        """获取文件内容预览"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(max_length)
                if len(content) == max_length:
                    content += '...'
                return content
        except UnicodeDecodeError:
            # 尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read(max_length)
                        if len(content) == max_length:
                            content += '...'
                        return content
                except UnicodeDecodeError:
                    continue
            return '[无法读取文件内容]'
    
    def _count_lines_and_words(self, file_path: str) -> tuple:
        """统计文件的行数和字数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                words = len(content.split())
                return len(lines), words
        except UnicodeDecodeError:
            return 0, 0
    
    def _read_text_file(self, file_path: str) -> List[str]:
        """读取文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按段落分割
            sections = re.split(r'\n\s*\n', content)
            return [s.strip() for s in sections if s.strip()]
        except UnicodeDecodeError:
            # 尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    sections = re.split(r'\n\s*\n', content)
                    return [s.strip() for s in sections if s.strip()]
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"无法读取文件: {file_path}")
    
    def _read_markdown_file(self, file_path: str) -> List[str]:
        """读取Markdown文件"""
        content = self._read_text_file(file_path)
        
        # 按标题分割
        sections = []
        current_section = []
        
        for line in content:
            if re.match(r'^#{1,6}\s+', line):
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = []
            current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        return [s.strip() for s in sections if s.strip()]
    
    def _read_docx_file(self, file_path: str) -> List[str]:
        """读取Word文档"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx 未安装，无法读取 .docx 文件")
        
        try:
            doc = docx.Document(file_path)
            sections = []
            current_section = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    # 检查是否是标题
                    if paragraph.style.name.startswith('Heading'):
                        if current_section:
                            sections.append('\n'.join(current_section))
                            current_section = []
                    current_section.append(text)
            
            if current_section:
                sections.append('\n'.join(current_section))
            
            return [s for s in sections if s.strip()]
        except Exception as e:
            self.logger.error(f"读取Word文档失败: {e}")
            raise
    
    def _read_pdf_file(self, file_path: str) -> List[str]:
        """读取PDF文件"""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 未安装，无法读取 .pdf 文件")
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                content = []
                
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        content.append(text.strip())
                
                # 按段落分割
                full_text = '\n'.join(content)
                sections = re.split(r'\n\s*\n', full_text)
                return [s.strip() for s in sections if s.strip()]
        except Exception as e:
            self.logger.error(f"读取PDF文件失败: {e}")
            raise
    
    def _read_csv_file(self, file_path: str) -> List[str]:
        """读取CSV文件"""
        if not EXCEL_AVAILABLE:
            raise ImportError("pandas 未安装，无法读取 .csv 文件")
        
        try:
            df = pd.read_csv(file_path)
            sections = []
            
            # 将每行转换为文本
            for index, row in df.iterrows():
                row_text = ' | '.join([f"{col}: {val}" for col, val in row.items()])
                sections.append(row_text)
            
            return sections
        except Exception as e:
            self.logger.error(f"读取CSV文件失败: {e}")
            raise
    
    def _read_excel_file(self, file_path: str) -> List[str]:
        """读取Excel文件"""
        if not EXCEL_AVAILABLE:
            raise ImportError("pandas 未安装，无法读取 .xlsx/.xls 文件")
        
        try:
            # 读取所有工作表
            excel_file = pd.ExcelFile(file_path)
            sections = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # 添加工作表标题
                sections.append(f"工作表: {sheet_name}")
                
                # 将每行转换为文本
                for index, row in df.iterrows():
                    row_text = ' | '.join([f"{col}: {val}" for col, val in row.items()])
                    sections.append(row_text)
            
            return sections
        except Exception as e:
            self.logger.error(f"读取Excel文件失败: {e}")
            raise
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """验证文件"""
        result = {
            'valid': False,
            'errors': [],
            'warnings': []
        }
        
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                result['errors'].append('文件不存在')
                return result
            
            # 检查文件大小
            file_size = path.stat().st_size
            if file_size > 50 * 1024 * 1024:  # 50MB
                result['warnings'].append('文件大小超过50MB，可能影响处理速度')
            
            # 检查文件类型
            if not self.is_supported_file(file_path):
                result['errors'].append(f'不支持的文件类型: {path.suffix}')
                return result
            
            # 检查文件是否可读
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read(1024)  # 尝试读取前1KB
            except UnicodeDecodeError:
                result['warnings'].append('文件编码可能不是UTF-8，将尝试自动检测')
            
            result['valid'] = True
            
        except Exception as e:
            result['errors'].append(f'验证文件时发生错误: {str(e)}')
        
        return result
