"""Web应用模块"""

import asyncio
import logging
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import concurrent.futures

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.card_generator import GenerationConfig, CardData
from src.utils.file_processor import FileProcessor
from src.web.error_handler import handle_api_error, handle_file_error
from src.web.history_handler import HistoryHandler


class WebAppConstants:
    """Web应用常量"""
    SECRET_KEY = 'anki-card-assistant-secret-key'
    TEMP_DIR_NAME = "anki_card_assistant"

    # 默认值
    DEFAULT_TEMPLATE = 'Quizify'
    DEFAULT_PROMPT_TYPE = 'cloze'
    DEFAULT_DECK_NAME = '默认牌组'
    DEFAULT_MODEL = 'Basic'

    # 错误信息
    ERRORS = {
        'NO_CONTENT': '请提供内容',
        'NO_FILE': '没有选择文件',
        'FILE_NOT_FOUND': '文件不存在或已过期',
        'NO_CARD_DATA': '请提供卡片数据',
        'INVALID_FILENAME': '无效的文件名',
        'RECORD_NOT_FOUND': '记录不存在',
        'INVALID_CARD_INDEX': '卡片索引无效'
    }

    # 成功信息
    SUCCESS = {
        'PROMPT_SAVED': '提示词内容保存成功',
        'PROMPT_RESET': '提示词内容已重置为原始版本',
        'SETTINGS_SAVED': '设置已保存',
        'EXPORT_FORMATS_UPDATED': '导出格式已更新'
    }


class WebAppHelper:
    """Web应用辅助类 - 合并原来的多个辅助类功能"""

    def __init__(self, logger):
        self.logger = logger

    # 响应处理方法
    @staticmethod
    def success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
        """统一的成功响应格式"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response)

    @staticmethod
    def error_response(error_msg: str, status_code: int = 500) -> tuple:
        """统一的错误响应格式"""
        return jsonify({
            'success': False,
            'error': error_msg
        }), status_code

    # 卡片数据处理方法
    @staticmethod
    def convert_to_card_objects(cards_data: List[Dict], deck_name: str = None) -> List:
        """将卡片数据转换为CardData对象"""
        cards = []
        for card_dict in cards_data:
            card = CardData(
                front=card_dict.get('front', ''),
                back=card_dict.get('back', ''),
                deck=card_dict.get('deck', deck_name or WebAppConstants.DEFAULT_DECK_NAME),
                tags=card_dict.get('tags', []),
                model=card_dict.get('model', WebAppConstants.DEFAULT_MODEL),
                fields=card_dict.get('fields', {})
            )
            cards.append(card)
        return cards

    @staticmethod
    def serialize_cards(cards: List) -> List[Dict]:
        """将CardData对象序列化为字典"""
        return [c.to_dict() if hasattr(c, 'to_dict') else c for c in cards]

    # 配置处理方法
    @staticmethod
    def get_generation_config(data: dict, card_assistant) -> GenerationConfig:
        """获取生成配置"""
        return GenerationConfig(
            template_name=data.get('template', WebAppConstants.DEFAULT_TEMPLATE),
            prompt_type=data.get('prompt_type', WebAppConstants.DEFAULT_PROMPT_TYPE),
            card_count=data.get('card_count', card_assistant.config["generation"]["default_card_count"]),
            custom_deck_name=data.get('deck_name'),
            difficulty=data.get('difficulty', card_assistant.config["generation"]["default_difficulty"])
        )

    @staticmethod
    def ensure_json_in_formats(export_formats: list) -> list:
        """确保导出格式中包含JSON"""
        if 'json' not in export_formats:
            export_formats.insert(0, 'json')
        return export_formats

    # 异步任务处理方法
    def run_async_task(self, coro):
        """运行异步任务的辅助方法"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_coro_in_thread, coro)
            return future.result()

    def _run_coro_in_thread(self, coro):
        """在线程中运行协程"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        except (RuntimeError, OSError, asyncio.TimeoutError) as e:
            self.logger.error("在线程中运行协程失败: %s", e)
            raise

    # 错误检测方法
    @staticmethod
    def is_cloudflare_error(error_text: str) -> bool:
        """检查是否为Cloudflare错误"""
        cf_markers = ['cf-error-details', 'Cloudflare Ray ID', '/cdn-cgi/',
                      'Attention Required! | Cloudflare']
        return any(marker in error_text for marker in cf_markers)

    @staticmethod
    def is_html_response(error_text: str) -> bool:
        """检查是否为HTML响应"""
        return ('<!DOCTYPE html>' in error_text) or ('<html' in error_text.lower())


class WebApp:
    """Web应用类"""

    def __init__(self, card_assistant):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = WebAppConstants.SECRET_KEY
        CORS(self.app)

        # 配置SocketIO
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=True,
            engineio_logger=True
        )

        # 核心组件
        self.assistant = card_assistant
        self.logger = logging.getLogger(__name__)
        self.file_processor = FileProcessor()
        self.history_handler = HistoryHandler(
            self.assistant.config["export"]["output_directory"]
        )

        # 统一的辅助工具
        self.helper = WebAppHelper(self.logger)

        # 创建临时文件目录
        self.temp_dir = Path(tempfile.gettempdir()) / WebAppConstants.TEMP_DIR_NAME
        self.temp_dir.mkdir(exist_ok=True)

        # 注册路由和事件
        self._register_all_routes()
        self._register_socket_events()

    def _handle_api_error(self, operation: str, error: Exception, status_code: int = 500):
        """统一的API错误处理"""
        error_msg = str(error)
        self.logger.error("%s失败: %s", operation, error_msg)
        return self.helper.error_response(error_msg, status_code)

    def _register_all_routes(self):
        """注册所有路由"""
        self._register_basic_routes()
        self._register_api_routes()
        self._register_file_routes()
        self._register_history_routes()

    def _register_basic_routes(self):
        """注册基础路由"""

        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(
                self.app.static_folder, 'favicon.ico',
                mimetype='image/vnd.microsoft.icon'
            )

    def _register_api_routes(self):
        """注册API路由"""

        # 基础信息路由
        self._register_info_routes()
        # 内容生成路由
        self._register_generation_routes()
        # 设置和配置路由
        self._register_settings_routes()

    def _register_info_routes(self):
        """注册信息获取路由"""

        @self.app.route('/api/templates')
        @handle_api_error
        def get_templates():
            templates = self.assistant.list_templates()
            return self.helper.success_response(data=templates)

        @self.app.route('/api/prompts')
        @handle_api_error
        def get_prompts():
            category = request.args.get('category')
            template_name = request.args.get('template')
            prompts = self.assistant.list_prompts(
                category=category, template_name=template_name
            )
            return self.helper.success_response(data=prompts)

        @self.app.route('/api/prompt-names')
        @handle_api_error
        def get_prompt_names():
            category = request.args.get('category')
            template_name = request.args.get('template')
            prompt_names = self.assistant.list_prompt_names(
                category=category, template_name=template_name
            )
            return self.helper.success_response(data=prompt_names)

        @self.app.route('/api/llm-clients')
        @handle_api_error
        def get_llm_clients():
            clients = self.assistant.list_llm_clients()
            return self.helper.success_response(data=clients)

    def _register_generation_routes(self):
        """注册内容生成路由"""

        @self.app.route('/api/generate', methods=['POST'])
        def generate_cards():
            try:
                data = request.get_json()
                content = data.get('content', '').strip()

                if not content:
                    return self.helper.error_response(
                        WebAppConstants.ERRORS['NO_CONTENT'], 400
                    )

                return self._process_card_generation(content, data)
            except (ValueError, KeyError, TypeError) as e:
                return self._handle_api_error("生成卡片", e, 400)
            except (RuntimeError, OSError) as e:
                return self._handle_api_error("生成卡片", e)

        @self.app.route('/api/test-llm', methods=['POST'])
        def test_llm():
            try:
                data = request.get_json(silent=True) or {}
                prompt = data.get('prompt') or 'Hi,Who are you?'

                reply = self.helper.run_async_task(
                    self.assistant.llm_manager.generate_text(prompt)
                )

                return self.helper.success_response(data={'reply': reply})
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                return self._handle_llm_test_error(e)

    def _register_settings_routes(self):
        """注册设置和配置路由"""

        @self.app.route('/api/prompt-content')
        def get_prompt_content():
            try:
                prompt_type = request.args.get('prompt_type')
                template_name = request.args.get('template')
                if not prompt_type:
                    return self.helper.error_response('请提供提示词类型', 400)

                prompt_content = self.assistant.get_prompt_content(
                    prompt_type, template_name
                )
                return self.helper.success_response(data={
                    'content': prompt_content,
                    'prompt_type': prompt_type
                })
            except (FileNotFoundError, KeyError) as e:
                return self._handle_api_error("获取提示词内容", e, 404)
            except (ValueError, TypeError) as e:
                return self._handle_api_error("获取提示词内容", e, 400)

        @self.app.route('/api/prompt-content', methods=['POST'])
        def save_prompt_content():
            try:
                data = request.get_json()
                prompt_type = data.get('prompt_type')
                content = data.get('content')
                template_name = data.get('template')

                if not prompt_type or not content:
                    return self.helper.error_response('请提供提示词类型和内容', 400)

                self.assistant.save_prompt_content(prompt_type, content, template_name)
                return self.helper.success_response(
                    message=WebAppConstants.SUCCESS['PROMPT_SAVED']
                )
            except (FileNotFoundError, PermissionError) as e:
                return self._handle_api_error("保存提示词内容", e, 403)
            except (ValueError, TypeError) as e:
                return self._handle_api_error("保存提示词内容", e, 400)

        @self.app.route('/api/prompt-content/reset', methods=['POST'])
        def reset_prompt_content():
            try:
                data = request.get_json()
                prompt_type = data.get('prompt_type')
                template_name = data.get('template')

                if not prompt_type:
                    return self.helper.error_response('请提供提示词类型', 400)

                original_content = self.assistant.reset_prompt_content(
                    prompt_type, template_name
                )
                return self.helper.success_response(
                    data={
                        'content': original_content,
                        'prompt_type': prompt_type
                    },
                    message=WebAppConstants.SUCCESS['PROMPT_RESET']
                )
            except (FileNotFoundError, KeyError) as e:
                return self._handle_api_error("重置提示词内容", e, 404)

        @self.app.route('/api/settings')
        @handle_api_error
        def get_settings():
            settings = {
                'llm': {
                    'api_key': self.assistant.config.get('llm', {}).get('api_key', ''),
                    'base_url': self.assistant.config.get('llm', {}).get(
                        'base_url', 'https://api.openai.com/v1'
                    ),
                    'model': self.assistant.config.get('llm', {}).get(
                        'model', 'gpt-3.5-turbo'
                    ),
                    'temperature': self.assistant.config.get('llm', {}).get(
                        'temperature', 0.7
                    ),
                    'max_tokens': self.assistant.config.get('llm', {}).get(
                        'max_tokens', 20000
                    ),
                    'timeout': self.assistant.config.get('llm', {}).get('timeout', 30)
                }
            }
            return self.helper.success_response(data=settings)

        @self.app.route('/api/settings', methods=['POST'])
        def save_settings():
            try:
                data = request.get_json()
                if 'llm' in data:
                    self._update_llm_settings(data['llm'])

                try:
                    self.assistant.save_user_settings()
                except (FileNotFoundError, PermissionError) as e:
                    self.logger.warning("持久化用户设置失败: %s", e)

                return self.helper.success_response(
                    message=WebAppConstants.SUCCESS['SETTINGS_SAVED']
                )
            except (ValueError, TypeError) as e:
                return self._handle_api_error("保存设置", e, 400)

        @self.app.route('/api/config')
        @handle_api_error
        def get_config():
            return self.helper.success_response(data={
                'generation': self.assistant.config.get("generation", {}),
                'llm': self.assistant.config.get("llm", {}),
                'export': self.assistant.config.get("export", {})
            })

    def _register_file_routes(self):
        """注册文件相关路由"""

        @self.app.route('/api/upload-file', methods=['POST'])
        @handle_file_error
        def upload_file():
            if 'file' not in request.files:
                return self.helper.error_response(
                    WebAppConstants.ERRORS['NO_FILE'], 400
                )

            file = request.files['file']
            if file.filename == '':
                return self.helper.error_response(
                    WebAppConstants.ERRORS['NO_FILE'], 400
                )

            return self._process_file_upload(file)

        @self.app.route('/api/generate-from-file', methods=['POST'])
        def generate_from_file():
            try:
                data = request.get_json()
                temp_file_path = data.get('temp_file_path')
                selected_sections = data.get('selected_sections', [])

                if not temp_file_path or not Path(temp_file_path).exists():
                    return self.helper.error_response(
                        WebAppConstants.ERRORS['FILE_NOT_FOUND'], 400
                    )

                return self._process_file_generation(temp_file_path, selected_sections, data)
            except (FileNotFoundError, PermissionError) as e:
                return self._handle_api_error("从文件生成卡片", e, 404)
            except (ValueError, TypeError) as e:
                return self._handle_api_error("从文件生成卡片", e, 400)

        @self.app.route('/api/supported-file-types')
        @handle_api_error
        def get_supported_file_types():
            extensions = self.file_processor.get_supported_extensions()
            return self.helper.success_response(data=extensions)

        @self.app.route('/api/export-apkg', methods=['POST'])
        def export_apkg():
            try:
                data = request.get_json()
                cards_data = data.get('cards', [])
                template_name = data.get('template_name', None)
                filename = data.get('filename', None)

                if not cards_data:
                    return self.helper.error_response(
                        WebAppConstants.ERRORS['NO_CARD_DATA'], 400
                    )

                return self._process_apkg_export(cards_data, template_name, filename)
            except (ValueError, TypeError) as e:
                return self._handle_api_error("导出apkg", e, 400)
            except (FileNotFoundError, PermissionError) as e:
                return self._handle_api_error("导出apkg", e, 403)

        @self.app.route('/api/update-export-formats', methods=['POST'])
        def update_export_formats():
            try:
                data = request.get_json()
                export_formats = data.get('export_formats', [])
                export_formats = self.helper.ensure_json_in_formats(export_formats)

                self.assistant.config_manager.set(
                    'export.default_formats', export_formats
                )
                self.assistant.config_manager.save_config()

                return self.helper.success_response(
                    message=WebAppConstants.SUCCESS['EXPORT_FORMATS_UPDATED']
                )
            except (ValueError, TypeError) as e:
                return self._handle_api_error("更新导出格式", e, 400)
            except (FileNotFoundError, PermissionError) as e:
                return self._handle_api_error("更新导出格式", e, 403)

        @self.app.route('/api/download-all', methods=['POST'])
        def download_all_files():
            try:
                data = request.get_json()
                cards_data = data.get('cards', [])
                deck_name = data.get('deck_name', 'AI生成卡片')
                export_formats = data.get('export_formats', ['json'])

                if not cards_data:
                    return self.helper.error_response(
                        WebAppConstants.ERRORS['NO_CARD_DATA'], 400
                    )

                return self._create_download_archive(cards_data, deck_name, export_formats)
            except (ValueError, TypeError) as e:
                return self._handle_api_error("生成压缩包", e, 400)
            except (FileNotFoundError, PermissionError) as e:
                return self._handle_api_error("生成压缩包", e, 403)

        @self.app.route('/download/<path:filename>')
        @handle_file_error
        def download_file(filename):
            return self._handle_file_download(filename)

    def _register_history_routes(self):
        """注册历史记录路由"""

        @self.app.route('/api/history')
        @handle_api_error
        def get_history():
            history_records = self.history_handler.get_history_records()
            return self.helper.success_response(data=history_records)

        @self.app.route('/api/history/<record_id>/detail')
        def get_history_detail(record_id):
            try:
                detail_data = self.history_handler.get_history_detail(record_id)
                if detail_data is None:
                    return self.helper.error_response(
                        WebAppConstants.ERRORS['RECORD_NOT_FOUND'], 404
                    )
                return self.helper.success_response(data=detail_data)
            except (FileNotFoundError, KeyError) as e:
                return self._handle_api_error("获取历史记录详情", e, 404)

        @self.app.route('/api/history/<record_id>/download/<file_type>')
        @handle_file_error
        def download_history_file(record_id, file_type):
            return self._handle_history_file_download(record_id, file_type)

        @self.app.route('/api/history/<record_id>/card/<int:card_index>')
        def get_history_card(record_id, card_index):
            try:
                card_data = self.history_handler.get_history_card(record_id, card_index)
                if card_data is None:
                    history_file = Path(
                        self.assistant.config["export"]["output_directory"]
                    ).joinpath(f"{record_id}.json")
                    if not history_file.exists():
                        return self.helper.error_response(
                            WebAppConstants.ERRORS['RECORD_NOT_FOUND'], 404
                        )
                    return self.helper.error_response(
                        WebAppConstants.ERRORS['INVALID_CARD_INDEX'], 400
                    )
                return self.helper.success_response(data=card_data)
            except (FileNotFoundError, KeyError, IndexError) as e:
                return self._handle_api_error("获取历史记录卡片", e, 404)

        @self.app.route('/api/history/<record_id>', methods=['DELETE'])
        def delete_history_record(record_id):
            try:
                deleted_files = self.history_handler.delete_history_record(record_id)
                return self.helper.success_response(
                    message=f'已删除 {len(deleted_files)} 个文件',
                    data={'deleted_files': deleted_files}
                )
            except (FileNotFoundError, PermissionError) as e:
                return self._handle_api_error("删除历史记录", e, 403)

    def _register_socket_events(self):
        """注册Socket.IO事件"""

        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('客户端已连接')
            emit('status', {'message': '已连接到Anki写卡助手'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info('客户端已断开连接')

        @self.socketio.on('generate_cards')
        def handle_generate_cards(data):
            try:
                content = data.get('content', '').strip()
                if not content:
                    emit('generation_error', {
                        'error': WebAppConstants.ERRORS['NO_CONTENT']
                    })
                    return

                emit('generation_start', {'message': '开始生成卡片...'})
                config = self.helper.get_generation_config(data, self.assistant)
                cards = self.helper.run_async_task(
                    self.assistant.generate_cards(content, config)
                )

                emit('generation_progress', {
                    'message': f'已生成 {len(cards)} 张卡片'
                })

                export_formats = data.get(
                    'export_formats', self.assistant.config["export"]["default_formats"]
                )
                export_formats = self.helper.ensure_json_in_formats(export_formats)
                export_paths = self.assistant.export_cards(cards, export_formats)

                summary = self.assistant.get_export_summary(cards)
                serializable_cards = self.helper.serialize_cards(cards)

                emit('generation_complete', {
                    'cards': serializable_cards,
                    'export_paths': export_paths,
                    'summary': summary
                })

            except (ValueError, KeyError, TypeError, RuntimeError) as e:
                self.logger.error("生成卡片失败: %s", e)
                emit('generation_error', {'error': str(e)})

    # 辅助处理方法
    def _process_card_generation(self, content: str, data: dict):
        """处理卡片生成"""
        config = self.helper.get_generation_config(data, self.assistant)
        cards = self.helper.run_async_task(
            self.assistant.generate_cards(content, config)
        )

        export_formats = data.get(
            'export_formats', self.assistant.config["export"]["default_formats"]
        )
        export_formats = self.helper.ensure_json_in_formats(export_formats)
        export_paths = self.assistant.export_cards(
            cards, export_formats,
            original_content=content,
            generation_config={
                'template_name': config.template_name,
                'prompt_type': config.prompt_type,
                'card_count': config.card_count,
                'custom_deck_name': config.custom_deck_name,
                'difficulty': config.difficulty
            }
        )

        summary = self.assistant.get_export_summary(cards)
        serializable_cards = self.helper.serialize_cards(cards)

        return self.helper.success_response(data={
            'cards': serializable_cards,
            'export_paths': export_paths,
            'summary': summary
        })

    def _process_file_upload(self, file):
        """处理文件上传"""
        if not self.file_processor.is_supported_file(file.filename):
            supported_extensions = self.file_processor.get_supported_extensions()
            return self.helper.error_response(
                f'不支持的文件类型。支持的类型: {", ".join(supported_extensions)}', 400
            )

        temp_file_path = self.temp_dir / file.filename
        file.save(temp_file_path)

        validation_result = self.file_processor.validate_file(str(temp_file_path))
        if not validation_result['valid']:
            temp_file_path.unlink(missing_ok=True)
            return self.helper.error_response(
                f'文件验证失败: {", ".join(validation_result["errors"])}', 400
            )

        processed_content = self.file_processor.process_file(str(temp_file_path))

        return self.helper.success_response(data={
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

    def _process_file_generation(self, temp_file_path: str,
                                 selected_sections: List[int], data: dict):
        """处理从文件生成卡片"""
        processed_content = self.file_processor.process_file(temp_file_path)

        if selected_sections:
            sections_to_process = [
                processed_content.sections[i] for i in selected_sections
                if i < len(processed_content.sections)
            ]
        else:
            sections_to_process = processed_content.sections

        if not sections_to_process:
            return self.helper.error_response('没有可处理的内容', 400)

        config = self.helper.get_generation_config(data, self.assistant)
        combined_content = '\n\n'.join(sections_to_process)
        cards = self.helper.run_async_task(
            self.assistant.generate_cards(combined_content, config)
        )

        export_formats = data.get(
            'export_formats', self.assistant.config["export"]["default_formats"]
        )
        export_formats = self.helper.ensure_json_in_formats(export_formats)
        export_paths = self.assistant.export_cards(
            cards, export_formats,
            original_content=combined_content,
            generation_config={
                'template_name': config.template_name,
                'prompt_type': config.prompt_type,
                'card_count': config.card_count,
                'custom_deck_name': config.custom_deck_name,
                'difficulty': config.difficulty,
                'source_file': processed_content.original_file.filename
            }
        )

        summary = self.assistant.get_export_summary(cards)
        serializable_cards = self.helper.serialize_cards(cards)

        return self.helper.success_response(data={
            'cards': serializable_cards,
            'export_paths': export_paths,
            'summary': summary,
            'processed_sections': len(sections_to_process)
        })

    def _process_apkg_export(self, cards_data: List[Dict],
                             template_name: Optional[str], filename: Optional[str]):
        """处理APKG导出"""
        cards = self.helper.convert_to_card_objects(cards_data)

        if template_name:
            export_path = self.assistant.export_apkg_with_custom_template(
                cards, template_name, filename
            )
        else:
            export_path = self.assistant.export_apkg(cards, filename)

        return self.helper.success_response(data={
            'export_path': export_path,
            'filename': Path(export_path).name
        })

    def _create_download_archive(self, cards_data: List[Dict],
                                 deck_name: str, export_formats: List[str]):
        """创建下载压缩包"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"anki_cards_{timestamp}.zip"
        output_dir = Path(self.assistant.config["export"]["output_directory"])
        zip_path = output_dir / zip_filename

        cards = self.helper.convert_to_card_objects(cards_data, deck_name)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            base_filename = f"anki_cards_{timestamp}"

            for format_type in export_formats:
                try:
                    if format_type == 'apkg':
                        export_path = self.assistant.export_apkg(
                            cards, f"{base_filename}.apkg"
                        )
                    else:
                        export_path = self.assistant.export_cards(cards, [format_type])
                        if format_type in export_path:
                            export_path = export_path[format_type]
                        else:
                            continue

                    if Path(export_path).exists():
                        zipf.write(export_path, Path(export_path).name)
                        self.logger.info("已添加文件到压缩包: %s", export_path)

                except (OSError, ValueError) as e:
                    self.logger.warning("生成%s格式文件失败: %s", format_type, e)
                    continue

        self.logger.info("压缩包生成成功: %s", zip_path)

        return self.helper.success_response(data={
            'filename': zip_filename,
            'file_path': str(zip_path),
            'card_count': len(cards)
        })

    def _handle_file_download(self, filename: str):
        """处理文件下载"""
        app_root = Path(self.app.root_path).parent.parent
        output_dir = app_root / "output"

        filename = filename.replace('\\', '/').strip('/')
        if filename.startswith('output/'):
            filename = filename[7:]
        elif filename.startswith('output\\'):
            filename = filename[8:]

        if '..' in filename or filename.startswith('/'):
            return self.helper.error_response(
                WebAppConstants.ERRORS['INVALID_FILENAME'], 400
            )

        file_path = output_dir / filename

        self.logger.info("下载请求: %s", filename)
        self.logger.info("文件完整路径: %s", file_path)

        if not file_path.exists():
            self.logger.error("文件不存在: %s", file_path)
            if output_dir.exists():
                files = list(output_dir.glob('*'))
                self.logger.info("Output目录中的文件: %s", [f.name for f in files])
            else:
                self.logger.error("Output目录不存在: %s", output_dir)
            return self.helper.error_response(
                WebAppConstants.ERRORS['FILE_NOT_FOUND'], 404
            )

        return send_from_directory(
            str(output_dir),
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    def _handle_history_file_download(self, record_id: str, file_type: str):
        """处理历史文件下载"""
        output_dir = Path(
            self.assistant.config["export"]["output_directory"]
        ).resolve()
        file_path = output_dir / f"{record_id}.{file_type}"

        self.logger.info("下载请求: record_id=%s, file_type=%s", record_id, file_type)
        self.logger.info("文件路径: %s", file_path)

        if not file_path.exists():
            self.logger.warning("文件不存在: %s", file_path)
            return self.helper.error_response(
                WebAppConstants.ERRORS['FILE_NOT_FOUND'], 404
            )

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    def _update_llm_settings(self, llm_settings: dict):
        """更新LLM设置"""
        llm_config = self.assistant.config.setdefault('llm', {})

        for key, value in llm_settings.items():
            if key in ['temperature', 'max_tokens', 'timeout']:
                llm_config[key] = type(value)(value) if value else value
            else:
                llm_config[key] = value

        self.assistant.update_llm_config(llm_settings)

    def _handle_llm_test_error(self, error: Exception):
        """处理LLM测试错误"""
        err_text = str(error)
        base_url = self.assistant.config.get('llm', {}).get('base_url', '')

        if self.helper.is_cloudflare_error(err_text):
            err_text = (
                f'请求可能被Cloudflare防护拦截（{base_url}）。'
                '请在"AI设置"中将 API 基础URL(base_url) 换为可直连、无浏览器质询的后端域名，'
                '例如官方 OpenAI: https://api.openai.com/v1，'
                '或你的服务商提供的后端专用域名/加速地址。'
            )
        elif self.helper.is_html_response(err_text):
            err_text = (
                f'目标返回HTML页面（{base_url}）。可能是网关/反向代理错误或需要浏览器验证。'
                '请检查 base_url 是否正确指向后端API地址，并确认网络可直连；'
                '如使用第三方服务商，请使用其后端API域名。'
            )

        self.logger.error("API测试失败: %s", err_text)
        return self.helper.error_response(err_text, 500)

    def run(self, host='0.0.0.0', port=5000, debug=False):
        """运行Web应用"""
        self.logger.info("启动Web服务器: http://%s:%s", host, port)
        self.socketio.run(
            self.app, host=host, port=port, debug=debug,
            use_reloader=debug, allow_unsafe_werkzeug=True
        )


def create_app(card_assistant=None):
    """创建Flask应用实例"""
    if card_assistant is None:
        from main import AnkiCardAssistant
        card_assistant = AnkiCardAssistant()

    web_app = WebApp(card_assistant)
    return web_app.app


if __name__ == '__main__':
    from main import AnkiCardAssistant
    main_assistant = AnkiCardAssistant()
    main_web_app = WebApp(main_assistant)
    main_web_app.run(debug=True)
