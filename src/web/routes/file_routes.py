"""文件路由模块"""

import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from flask import request, send_from_directory, send_file

from src.web.error_handler import handle_file_error, handle_api_error, handle_validation_error
from src.web.utils import ResponseUtils, ValidationUtils, FileUtils, DateTimeUtils, ArchiveUtils


class FileRoutes:
    """文件路由处理类"""
    
    def __init__(self, app, assistant, business_logic, file_processor, temp_dir):
        self.app = app
        self.assistant = assistant
        self.business_logic = business_logic
        self.file_processor = file_processor
        self.temp_dir = temp_dir
        self.register_routes()
    
    def register_routes(self):
        """注册文件相关路由"""

        @self.app.route('/api/upload-file', methods=['POST'])
        @handle_file_error
        def upload_file():
            if 'file' not in request.files:
                return ResponseUtils.error_response('没有选择文件', 400)

            file = request.files['file']
            if file.filename == '':
                return ResponseUtils.error_response('没有选择文件', 400)

            return self._process_file_upload(file)

        @self.app.route('/api/generate-from-file', methods=['POST'])
        @handle_validation_error
        def generate_from_file():
            data = request.get_json()
            temp_file_path = data.get('temp_file_path')
            selected_sections = data.get('selected_sections', [])

            if not temp_file_path or not Path(temp_file_path).exists():
                return ResponseUtils.error_response('文件不存在或已过期', 400)

            result = self.business_logic.process_file_generation(
                temp_file_path, selected_sections, data, self.file_processor
            )
            return ResponseUtils.success_response(data=result)

        @self.app.route('/api/supported-file-types')
        @handle_api_error
        def get_supported_file_types():
            extensions = self.file_processor.get_supported_extensions()
            return ResponseUtils.success_response(data=extensions)

        @self.app.route('/api/export-apkg', methods=['POST'])
        @handle_validation_error
        def export_apkg():
            data = request.get_json()
            cards_data = data.get('cards', [])
            template_name = data.get('template_name', None)
            filename = data.get('filename', None)

            if not cards_data:
                return ResponseUtils.error_response('请提供卡片数据', 400)

            result = self.business_logic.process_apkg_export(
                cards_data, template_name, filename
            )
            return ResponseUtils.success_response(data=result)

        @self.app.route('/api/update-export-formats', methods=['POST'])
        @handle_validation_error
        def update_export_formats():
            data = request.get_json()
            export_formats = data.get('export_formats', [])
            export_formats = self.business_logic.config_processor.ensure_json_in_formats(export_formats)

            self.assistant.config_manager.set(
                'export.default_formats', export_formats
            )
            self.assistant.config_manager.save_config()

            return ResponseUtils.success_response(message='导出格式已更新')

        @self.app.route('/api/download-all', methods=['POST'])
        @handle_validation_error
        def download_all_files():
            data = request.get_json()
            cards_data = data.get('cards', [])
            deck_name = data.get('deck_name', 'AI生成卡片')
            export_formats = data.get('export_formats', ['json'])

            if not cards_data:
                return ResponseUtils.error_response('请提供卡片数据', 400)

            result = self._create_download_archive(cards_data, deck_name, export_formats)
            return ResponseUtils.success_response(data=result)

        @self.app.route('/download/<path:filename>')
        @handle_file_error
        def download_file(filename):
            return self._handle_file_download(filename)

    def _process_file_upload(self, file):
        """处理文件上传"""
        if not self.file_processor.is_supported_file(file.filename):
            supported_extensions = self.file_processor.get_supported_extensions()
            return ResponseUtils.error_response(
                f'不支持的文件类型。支持的类型: {", ".join(supported_extensions)}', 400
            )

        temp_file_path = self.temp_dir / file.filename
        file.save(temp_file_path)

        validation_result = self.file_processor.validate_file(str(temp_file_path))
        if not validation_result['valid']:
            FileUtils.delete_file_safely(temp_file_path)
            return ResponseUtils.error_response(
                f'文件验证失败: {", ".join(validation_result["errors"])}', 400
            )

        processed_content = self.file_processor.process_file(str(temp_file_path))

        return ResponseUtils.success_response(data={
            'file_info': {
                'filename': processed_content.original_file.filename,
                'file_size': processed_content.original_file.file_size,
                'file_type': processed_content.original_file.file_type,
                'total_lines': processed_content.original_file.total_lines,
                'total_words': processed_content.original_file.total_words,
                'content_preview': processed_content.original_file.content_preview
            },
            'sections': processed_content.sections,
            'section_count': len(processed_content.sections),
            'temp_file_path': str(temp_file_path),
            'warnings': validation_result.get('warnings', [])
        })

    def _create_download_archive(self, cards_data: List[Dict],
                                 deck_name: str, export_formats: List[str]):
        """创建下载压缩包 - 修复版本：不创建新文件，只打包现有文件"""
        output_dir = Path(self.assistant.config["export"]["output_directory"])

        # 查找output目录中最新的文件集
        existing_files = self._find_latest_export_files(output_dir, export_formats)
        
        if not existing_files:
            # 如果没有找到现有文件，说明可能是首次导出，需要生成文件
            self.business_logic.logger.warning("未找到现有导出文件，将生成新文件")
            return self._create_archive_with_new_files(cards_data, deck_name, export_formats)
        
        # 从现有文件中提取基础文件名（不带扩展名）
        base_filename = self._extract_base_filename_from_files(existing_files)
        if not base_filename:
            # 如果无法提取基础文件名，使用新时间戳
            base_filename = f"anki_cards_{DateTimeUtils.generate_timestamp()}"
        
        # 生成ZIP文件名，使用与原文件相同的基础名称
        zip_filename = f"{base_filename}.zip"
        zip_path = output_dir / zip_filename

        # 使用现有文件创建压缩包
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for format_type, file_path in existing_files.items():
                if Path(file_path).exists():
                    # 保持原始文件名
                    archive_name = Path(file_path).name
                    zipf.write(file_path, archive_name)
                    self.business_logic.logger.info("已添加现有文件到压缩包: %s -> %s", file_path, archive_name)

        self.business_logic.logger.info("压缩包生成成功（使用现有文件）: %s", zip_path)

        return {
            'filename': zip_filename,
            'file_path': str(zip_path),
            'card_count': len(cards_data)
        }

    def _find_latest_export_files(self, output_dir: Path, export_formats: List[str]) -> Dict[str, str]:
        """查找output目录中最新的导出文件"""
        existing_files = {}
        
        if not output_dir.exists():
            return existing_files
        
        # 为每种格式查找最新的文件
        for format_type in export_formats:
            pattern = f"anki_cards_*.{format_type}"
            matching_files = list(output_dir.glob(pattern))
            
            if matching_files:
                # 按修改时间排序，获取最新的文件
                latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
                existing_files[format_type] = str(latest_file)
                self.business_logic.logger.info("找到%s格式的最新文件: %s", format_type, latest_file.name)
        
        return existing_files

    def _extract_base_filename_from_files(self, existing_files: Dict[str, str]) -> str:
        """从现有文件中提取基础文件名"""
        if not existing_files:
            return None
        
        # 取第一个文件来提取基础文件名
        first_file_path = next(iter(existing_files.values()))
        file_path = Path(first_file_path)
        
        # 提取不带扩展名的文件名
        base_name = file_path.stem
        self.business_logic.logger.info("提取的基础文件名: %s", base_name)
        
        return base_name

    def _create_archive_with_new_files(self, cards_data: List[Dict], deck_name: str, 
                                     export_formats: List[str]):
        """当没有现有文件时，创建新文件并打包（保持原有逻辑作为后备）"""
        output_dir = Path(self.assistant.config["export"]["output_directory"])
        cards = self.business_logic.card_processor.convert_to_card_objects(cards_data, deck_name)
        
        # 使用统一的导出方法，确保所有格式使用相同的时间戳
        try:
            export_paths = self.assistant.export_cards(cards, export_formats)
            
            # 从生成的文件中提取基础文件名
            if export_paths:
                first_export_path = next(iter(export_paths.values()))
                base_filename = Path(first_export_path).stem
                zip_filename = f"{base_filename}.zip"
                zip_path = output_dir / zip_filename
            else:
                # 如果没有生成任何文件，使用新时间戳
                timestamp = DateTimeUtils.generate_timestamp()
                zip_filename = f"anki_cards_{timestamp}.zip"
                zip_path = output_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for format_type, export_path in export_paths.items():
                    if Path(export_path).exists():
                        zipf.write(export_path, Path(export_path).name)
                        self.business_logic.logger.info("已添加新生成文件到压缩包: %s", export_path)

        except Exception as e:
            self.business_logic.logger.error("生成文件失败: %s", e)
            raise

        self.business_logic.logger.info("压缩包生成成功（使用新生成文件）: %s", zip_path)

        return {
            'filename': zip_filename,
            'file_path': str(zip_path),
            'card_count': len(cards)
        }

    def _handle_file_download(self, filename: str):
        """处理文件下载"""
        app_root = Path(self.app.root_path).parent.parent
        output_dir = app_root / "output"

        safe_filename = FileUtils.safe_filename(filename)
        if not safe_filename:
            return ResponseUtils.error_response('无效的文件名', 400)

        file_path = output_dir / safe_filename

        self.business_logic.logger.info("下载请求: %s", safe_filename)
        self.business_logic.logger.info("文件完整路径: %s", file_path)

        if not file_path.exists():
            self.business_logic.logger.error("文件不存在: %s", file_path)
            if output_dir.exists():
                files = list(output_dir.glob('*'))
                self.business_logic.logger.info("Output目录中的文件: %s", [f.name for f in files])
            else:
                self.business_logic.logger.error("Output目录不存在: %s", output_dir)
            return ResponseUtils.error_response('文件不存在或已过期', 404)

        return send_from_directory(
            str(output_dir),
            safe_filename,
            as_attachment=True,
            download_name=os.path.basename(safe_filename)
        )