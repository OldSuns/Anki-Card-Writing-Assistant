import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# 添加src目录到Python路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.card_generator import GenerationConfig
from src.utils.file_processor import FileProcessor

class WebApp:
    """Web应用类"""
    
    def __init__(self, assistant):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'anki-card-assistant-secret-key'
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 使用传入的助手实例
        self.assistant = assistant
        self.logger = logging.getLogger(__name__)
        
        # 初始化文件处理器
        self.file_processor = FileProcessor()
        
        # 创建临时文件目录
        self.temp_dir = Path(tempfile.gettempdir()) / "anki_card_assistant"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 注册路由
        self._register_routes()
        self._register_socket_events()
    
    def _handle_api_error(self, operation: str, error: Exception, status_code: int = 500):
        """统一的API错误处理"""
        error_msg = str(error)
        self.logger.error(f"{operation}失败: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), status_code
    
    def _success_response(self, data: Any = None, message: str = None):
        """统一的成功响应格式"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response)
    
    def _format_content_preview(self, content_preview):
        """安全地格式化内容预览"""
        if content_preview is None:
            return ''
        
        content_str = str(content_preview)
        if len(content_str) > 100:
            return content_str[:100] + '...'
        return content_str
    
    def _process_card_data(self, card, card_index):
        """处理卡片数据，统一格式"""
        if not isinstance(card, dict):
            return {
                'index': card_index,
                'front': '无效卡片数据',
                'back': '',
                'deck': '',
                'tags': [],
                'fields': {},
                'modelName': '',
                'deckName': ''
            }
        
        processed_card = {
            'index': card_index,
            'front': '',
            'back': '',
            'deck': '',
            'tags': [],
            'fields': card.get('fields', {}),
            'modelName': card.get('modelName', ''),
            'deckName': card.get('deckName', '')
        }
        
        # 获取正面内容
        if 'front' in card:
            processed_card['front'] = card['front']
        elif 'fields' in card and isinstance(card['fields'], dict):
            processed_card['front'] = card['fields'].get('Front', '')
        
        # 获取背面内容
        if 'back' in card:
            processed_card['back'] = card['back']
        elif 'fields' in card and isinstance(card['fields'], dict):
            processed_card['back'] = card['fields'].get('Back', '')
        
        # 获取牌组名称
        if 'deck' in card:
            processed_card['deck'] = card['deck']
        elif 'fields' in card and isinstance(card['fields'], dict):
            processed_card['deck'] = card['fields'].get('Deck', '')
        
        # 获取标签
        if 'tags' in card and isinstance(card['tags'], list):
            processed_card['tags'] = card['tags']
        elif 'fields' in card and isinstance(card['fields'], dict) and card['fields'].get('Tags'):
            processed_card['tags'] = card['fields']['Tags'].split()
        
        return processed_card
    
    def _register_routes(self):
        """注册路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html')
        
        @self.app.route('/api/templates')
        def get_templates():
            """获取可用模板"""
            try:
                templates = self.assistant.list_templates()
                return self._success_response(data=templates)
            except Exception as e:
                return self._handle_api_error("获取模板", e)
        
        @self.app.route('/api/prompts')
        def get_prompts():
            """获取可用提示词"""
            try:
                category = request.args.get('category')
                template_name = request.args.get('template')
                prompts = self.assistant.list_prompts(category=category, template_name=template_name)
                return self._success_response(data=prompts)
            except Exception as e:
                return self._handle_api_error("获取提示词", e)
        
        @self.app.route('/api/prompt-names')
        def get_prompt_names():
            """获取可用提示词名称（用于显示）"""
            try:
                category = request.args.get('category')
                template_name = request.args.get('template')
                prompt_names = self.assistant.list_prompt_names(category=category, template_name=template_name)
                return self._success_response(data=prompt_names)
            except Exception as e:
                return self._handle_api_error("获取提示词名称", e)
        
        @self.app.route('/api/prompt-content')
        def get_prompt_content():
            """获取提示词内容"""
            try:
                prompt_type = request.args.get('prompt_type')
                template_name = request.args.get('template')
                if not prompt_type:
                    return jsonify({
                        'success': False,
                        'error': '请提供提示词类型'
                    }), 400
                
                # 获取提示词内容（按模板优先）
                prompt_content = self.assistant.get_prompt_content(prompt_type, template_name)
                return jsonify({
                    'success': True,
                    'data': {
                        'content': prompt_content,
                        'prompt_type': prompt_type
                    }
                })
            except Exception as e:
                self.logger.error(f"获取提示词内容失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/prompt-content', methods=['POST'])
        def save_prompt_content():
            """保存提示词内容"""
            try:
                data = request.get_json()
                prompt_type = data.get('prompt_type')
                content = data.get('content')
                template_name = data.get('template')
                
                if not prompt_type or not content:
                    return jsonify({
                        'success': False,
                        'error': '请提供提示词类型和内容'
                    }), 400
                
                # 保存提示词内容（按模板优先）
                self.assistant.save_prompt_content(prompt_type, content, template_name)
                return jsonify({
                    'success': True,
                    'message': '提示词内容保存成功'
                })
            except Exception as e:
                self.logger.error(f"保存提示词内容失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/prompt-content/reset', methods=['POST'])
        def reset_prompt_content():
            """重置提示词内容"""
            try:
                data = request.get_json()
                prompt_type = data.get('prompt_type')
                template_name = data.get('template')
                
                if not prompt_type:
                    return jsonify({
                        'success': False,
                        'error': '请提供提示词类型'
                    }), 400
                
                # 重置提示词内容（按模板优先）
                original_content = self.assistant.reset_prompt_content(prompt_type, template_name)
                return jsonify({
                    'success': True,
                    'message': '提示词内容已重置为原始版本',
                    'data': {
                        'content': original_content,
                        'prompt_type': prompt_type
                    }
                })
            except Exception as e:
                self.logger.error(f"重置提示词内容失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/llm-clients')
        def get_llm_clients():
            """获取可用LLM客户端"""
            try:
                clients = self.assistant.list_llm_clients()
                return self._success_response(data=clients)
            except Exception as e:
                return self._handle_api_error("获取LLM客户端", e)
        
        @self.app.route('/api/generate', methods=['POST'])
        def generate_cards():
            """生成卡片"""
            try:
                data = request.get_json()
                content = data.get('content', '').strip()
                
                if not content:
                    return jsonify({
                        'success': False,
                        'error': '请提供内容'
                    }), 400
                
                # 构建生成配置
                config = GenerationConfig(
                    template_name=data.get('template', 'Quizify'),  # 默认使用Quizify模板
                    prompt_type=data.get('prompt_type', 'cloze'),   # 默认使用cloze提示词
                    card_count=data.get('card_count', self.assistant.config["generation"]["default_card_count"]),
                    custom_deck_name=data.get('deck_name'),
                    difficulty=data.get('difficulty', self.assistant.config["generation"]["default_difficulty"])
                )
                
                # 异步生成卡片
                cards = self._run_async_task(self.assistant.generate_cards(content, config))
                
                # 导出卡片
                export_formats = data.get('export_formats', self.assistant.config["export"]["default_formats"])
                if 'json' not in export_formats:
                    export_formats.insert(0, 'json')
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
                
                # 获取摘要
                summary = self.assistant.get_export_summary(cards)
                
                # 将CardData对象转换为可JSON序列化
                serializable_cards = [c.to_dict() if hasattr(c, 'to_dict') else c for c in cards]
                return jsonify({
                    'success': True,
                    'data': {
                        'cards': serializable_cards,
                        'export_paths': export_paths,
                        'summary': summary
                    }
                })
                
            except Exception as e:
                self.logger.error(f"生成卡片失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/upload-file', methods=['POST'])
        def upload_file():
            """上传文件"""
            try:
                if 'file' not in request.files:
                    return jsonify({
                        'success': False,
                        'error': '没有选择文件'
                    }), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        'success': False,
                        'error': '没有选择文件'
                    }), 400
                
                # 检查文件类型
                if not self.file_processor.is_supported_file(file.filename):
                    supported_extensions = self.file_processor.get_supported_extensions()
                    return jsonify({
                        'success': False,
                        'error': f'不支持的文件类型。支持的类型: {", ".join(supported_extensions)}'
                    }), 400
                
                # 保存文件到临时目录
                temp_file_path = self.temp_dir / file.filename
                file.save(temp_file_path)
                
                # 验证文件
                validation_result = self.file_processor.validate_file(str(temp_file_path))
                if not validation_result['valid']:
                    # 删除临时文件
                    temp_file_path.unlink(missing_ok=True)
                    return jsonify({
                        'success': False,
                        'error': f'文件验证失败: {", ".join(validation_result["errors"])}',
                        'warnings': validation_result.get('warnings', [])
                    }), 400
                
                # 处理文件
                processed_content = self.file_processor.process_file(str(temp_file_path))
                
                return jsonify({
                    'success': True,
                    'data': {
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
                    }
                })
                
            except Exception as e:
                self.logger.error(f"文件上传失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/generate-from-file', methods=['POST'])
        def generate_from_file():
            """从文件生成卡片"""
            try:
                data = request.get_json()
                temp_file_path = data.get('temp_file_path')
                selected_sections = data.get('selected_sections', [])  # 用户选择的章节
                
                if not temp_file_path or not Path(temp_file_path).exists():
                    return jsonify({
                        'success': False,
                        'error': '文件不存在或已过期'
                    }), 400
                
                # 处理文件
                processed_content = self.file_processor.process_file(temp_file_path)
                
                # 如果用户选择了特定章节，只处理这些章节
                if selected_sections:
                    sections_to_process = [processed_content.sections[i] for i in selected_sections if i < len(processed_content.sections)]
                else:
                    sections_to_process = processed_content.sections
                
                if not sections_to_process:
                    return jsonify({
                        'success': False,
                        'error': '没有可处理的内容'
                    }), 400
                
                # 构建生成配置
                config = GenerationConfig(
                    template_name=data.get('template', 'Quizify'),
                    prompt_type=data.get('prompt_type', 'cloze'),
                    card_count=data.get('card_count', self.assistant.config["generation"]["default_card_count"]),
                    custom_deck_name=data.get('deck_name'),
                    difficulty=data.get('difficulty', self.assistant.config["generation"]["default_difficulty"])
                )
                
                # 合并所有章节内容
                combined_content = '\n\n'.join(sections_to_process)
                
                # 异步生成卡片
                cards = self._run_async_task(self.assistant.generate_cards(combined_content, config))
                
                # 导出卡片
                export_formats = data.get('export_formats', self.assistant.config["export"]["default_formats"])
                if 'json' not in export_formats:
                    export_formats.insert(0, 'json')
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
                
                # 获取摘要
                summary = self.assistant.get_export_summary(cards)
                
                # 将CardData对象转换为可JSON序列化
                serializable_cards = [c.to_dict() if hasattr(c, 'to_dict') else c for c in cards]
                
                return jsonify({
                    'success': True,
                    'data': {
                        'cards': serializable_cards,
                        'export_paths': export_paths,
                        'summary': summary,
                        'processed_sections': len(sections_to_process)
                    }
                })
                
            except Exception as e:
                self.logger.error(f"从文件生成卡片失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/supported-file-types')
        def get_supported_file_types():
            """获取支持的文件类型"""
            try:
                extensions = self.file_processor.get_supported_extensions()
                return self._success_response(data=extensions)
            except Exception as e:
                return self._handle_api_error("获取支持的文件类型", e)
        
        @self.app.route('/api/settings')
        def get_settings():
            """获取应用设置"""
            try:
                # 获取当前设置
                settings = {
                    'llm': {
                        'api_key': self.assistant.config.get('llm', {}).get('api_key', ''),
                        'base_url': self.assistant.config.get('llm', {}).get('base_url', 'https://api.openai.com/v1'),
                        'model': self.assistant.config.get('llm', {}).get('model', 'gpt-3.5-turbo'),
                        'temperature': self.assistant.config.get('llm', {}).get('temperature', 0.7),
                        'max_tokens': self.assistant.config.get('llm', {}).get('max_tokens', 20000),
                        'timeout': self.assistant.config.get('llm', {}).get('timeout', 30)
                    }
                }
                
                return jsonify({
                    'success': True,
                    'data': settings
                })
            except Exception as e:
                self.logger.error(f"获取设置失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/settings', methods=['POST'])
        def save_settings():
            """保存应用设置"""
            try:
                data = request.get_json()
                
                # 更新LLM设置
                if 'llm' in data:
                    llm_settings = data['llm']
                    llm_config = self.assistant.config.setdefault('llm', {})
                    
                    # 更新各项设置
                    for key, value in llm_settings.items():
                        if key in ['temperature', 'max_tokens', 'timeout']:
                            llm_config[key] = type(value)(value) if value else value
                        else:
                            llm_config[key] = value
                    
                    # 更新LLM客户端
                    self.assistant.update_llm_config(llm_settings)
                
                # 持久化到用户设置
                try:
                    self.assistant.save_user_settings()
                except Exception as e:
                    self.logger.warning(f"持久化用户设置失败: {e}")

                return jsonify({
                    'success': True,
                    'message': '设置已保存'
                })
                
            except Exception as e:
                self.logger.error(f"保存设置失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/config')
        def get_config():
            """获取配置信息（兼容性保留）"""
            try:
                return jsonify({
                    'success': True,
                    'data': {
                        'generation': self.assistant.config.get("generation", {}),
                        'llm': self.assistant.config.get("llm", {}),
                        'export': self.assistant.config.get("export", {})
                    }
                })
            except Exception as e:
                self.logger.error(f"获取配置失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/export-apkg', methods=['POST'])
        def export_apkg():
            """导出apkg文件"""
            try:
                data = request.get_json()
                cards_data = data.get('cards', [])
                template_name = data.get('template_name', None)  # 改为template_name
                filename = data.get('filename', None)
                
                if not cards_data:
                    return jsonify({
                        'success': False,
                        'error': '请提供卡片数据'
                    }), 400
                
                # 将卡片数据转换为CardData对象
                from src.core.card_generator import CardData
                cards = []
                for card_dict in cards_data:
                    card = CardData(
                        front=card_dict.get('front', ''),
                        back=card_dict.get('back', ''),
                        deck=card_dict.get('deck', '默认牌组'),
                        tags=card_dict.get('tags', []),
                        model=card_dict.get('model', 'Basic'),
                        fields=card_dict.get('fields', {})
                    )
                    cards.append(card)
                
                # 导出apkg文件
                if template_name:
                    # 使用自定义模板
                    export_path = self.assistant.export_apkg_with_custom_template(
                        cards, template_name, filename
                    )
                else:
                    # 使用标准模板
                    export_path = self.assistant.export_apkg(cards, filename)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'export_path': export_path,
                        'filename': Path(export_path).name
                    }
                })
                
            except Exception as e:
                self.logger.error(f"导出apkg失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/update-export-formats', methods=['POST'])
        def update_export_formats():
            """更新配置文件中的导出格式"""
            try:
                data = request.get_json()
                export_formats = data.get('export_formats', [])
                # 强制包含 json
                if 'json' not in export_formats:
                    export_formats.insert(0, 'json')

                # 更新配置文件中的导出格式
                self.assistant.config_manager.set('export.default_formats', export_formats)
                self.assistant.config_manager.save_config()
                
                return jsonify({
                    'success': True,
                    'message': '导出格式已更新'
                })
                
            except Exception as e:
                self.logger.error(f"更新导出格式失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/history')
        def get_history():
            """获取历史生成记录"""
            try:
                import os
                from datetime import datetime
                
                output_dir = Path(self.assistant.config["export"]["output_directory"])
                history_records = []
                
                if output_dir.exists():
                    # 获取所有生成的文件
                    for file_path in output_dir.glob("anki_cards_*.json"):
                        try:
                            # 从文件名解析时间戳
                            filename = file_path.stem
                            if "_" in filename:
                                # 文件名格式: anki_cards_20250828_231020
                                # 需要解析: 20250828_231020
                                parts = filename.split("_")
                                if len(parts) >= 3:
                                    date_str = parts[-2]  # 20250828
                                    time_str = parts[-1]  # 231020
                                    
                                    # 解析日期和时间
                                    if len(date_str) == 8 and len(time_str) == 6:
                                        year = int(date_str[:4])
                                        month = int(date_str[4:6])
                                        day = int(date_str[6:8])
                                        hour = int(time_str[:2])
                                        minute = int(time_str[2:4])
                                        second = int(time_str[4:6])
                                        
                                        timestamp = datetime(year, month, day, hour, minute, second)
                                    else:
                                        # 回退到原始解析方式
                                        timestamp_str = f"{date_str}_{time_str}"
                                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                                else:
                                    # 如果格式不匹配，跳过此文件
                                    continue
                                
                                # 读取JSON文件获取详细信息
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    card_data = json.load(f)
                                
                                # 构建历史记录
                                # 支持新的JSON格式（包含metadata）和旧格式
                                if isinstance(card_data, dict) and 'metadata' in card_data:
                                    # 新格式：包含metadata
                                    metadata = card_data.get('metadata', {})
                                    cards_list = card_data.get('cards', [])
                                    
                                    record = {
                                        'id': filename,
                                        'timestamp': metadata.get('timestamp', timestamp.isoformat()),
                                        'timestamp_display': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                        'card_count': metadata.get('card_count', len(cards_list)),
                                        'deck_name': metadata.get('deck_name', '未知牌组'),
                                        'content_preview': self._format_content_preview(metadata.get('content_preview', '')),
                                        'files': {}
                                    }
                                elif isinstance(card_data, list):
                                    # 旧格式：直接是卡片列表
                                    cards_list = card_data
                                    
                                    # 尝试从第一个卡片中获取牌组信息
                                    deck_name = '未知牌组'
                                    content_preview = '从卡片数据生成'
                                    
                                    if cards_list and isinstance(cards_list[0], dict):
                                        first_card = cards_list[0]
                                        # 尝试从不同字段获取牌组名称
                                        deck_name = (
                                            first_card.get('deckName') or 
                                            first_card.get('deck') or 
                                            first_card.get('fields', {}).get('Deck') or 
                                            '未知牌组'
                                        )
                                        
                                        # 尝试从卡片内容生成预览
                                        front_content = ''
                                        if 'fields' in first_card and isinstance(first_card['fields'], dict):
                                            front_content = first_card['fields'].get('Front', '')
                                        elif 'front' in first_card:
                                            front_content = first_card['front']
                                        
                                        if front_content:
                                            # 清理HTML标签和特殊字符
                                            import re
                                            clean_content = re.sub(r'<[^>]+>', '', front_content)
                                            clean_content = re.sub(r'\{\{[^}]+\}\}', '', clean_content)
                                            content_preview = clean_content[:100] + '...' if len(clean_content) > 100 else clean_content
                                    
                                    record = {
                                        'id': filename,
                                        'timestamp': timestamp.isoformat(),
                                        'timestamp_display': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                        'card_count': len(cards_list),
                                        'deck_name': deck_name,
                                        'content_preview': content_preview,
                                        'files': {}
                                    }
                                else:
                                    # 未知格式，跳过
                                    continue
                                
                                # 检查相关文件是否存在
                                base_name = file_path.stem
                                for ext in ['json', 'csv', 'html', 'txt', 'apkg']:
                                    ext_file = output_dir / f"{base_name}.{ext}"
                                    if ext_file.exists():
                                        record['files'][ext] = {
                                            'exists': True,
                                            'size': ext_file.stat().st_size,
                                            'filename': ext_file.name
                                        }
                                    else:
                                        record['files'][ext] = {'exists': False}
                                
                                history_records.append(record)
                                
                        except Exception as e:
                            self.logger.warning(f"解析历史记录文件失败 {file_path}: {e}")
                            continue
                
                # 按时间倒序排列
                history_records.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return jsonify({
                    'success': True,
                    'data': history_records
                })
                
            except Exception as e:
                self.logger.error(f"获取历史记录失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/history/<record_id>/detail')
        def get_history_detail(record_id):
            """获取历史记录详情"""
            try:
                output_dir = Path(self.assistant.config["export"]["output_directory"])
                json_file = output_dir / f"{record_id}.json"
                
                if not json_file.exists():
                    return jsonify({
                        'success': False,
                        'error': '记录不存在'
                    }), 404
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    card_data = json.load(f)
                
                # 处理新的JSON格式（包含metadata）和旧格式
                if isinstance(card_data, dict) and 'metadata' in card_data:
                    # 新格式：包含metadata
                    cards_list = card_data.get('cards', [])
                    
                    # 处理卡片数据，确保格式统一
                    processed_cards = []
                    for i, card in enumerate(cards_list):
                        processed_card = self._process_card_data(card, i + 1)
                        processed_cards.append(processed_card)
                    
                    response_data = {
                        'timestamp': card_data['metadata'].get('timestamp'),
                        'deck_name': card_data['metadata'].get('deck_name', '未知牌组'),
                        'card_count': card_data['metadata'].get('card_count', len(processed_cards)),
                        'content_preview': self._format_content_preview(card_data['metadata'].get('content_preview', '')),
                        'generation_config': card_data['metadata'].get('generation_config', {}),
                        'cards': processed_cards,
                        'current_card_index': 0,  # 当前显示的卡片索引
                        'total_cards': len(processed_cards)
                    }
                elif isinstance(card_data, list):
                    # 旧格式：直接是卡片列表
                    deck_name = '未知牌组'
                    content_preview = '从卡片数据生成'
                    
                    # 处理卡片数据，确保格式统一
                    processed_cards = []
                    for i, card in enumerate(card_data):
                        processed_card = self._process_card_data(card, i + 1)
                        processed_cards.append(processed_card)
                    
                    if processed_cards:
                        first_card = processed_cards[0]
                        # 尝试从不同字段获取牌组名称
                        deck_name = (
                            first_card.get('deckName') or 
                            first_card.get('deck') or 
                            first_card.get('fields', {}).get('Deck') or 
                            '未知牌组'
                        )
                        
                        # 尝试从卡片内容生成预览
                        front_content = first_card.get('front', '')
                        
                        if front_content:
                            # 清理HTML标签和特殊字符
                            import re
                            clean_content = re.sub(r'<[^>]+>', '', front_content)
                            clean_content = re.sub(r'\{\{[^}]+\}\}', '', clean_content)
                            content_preview = clean_content[:200] + '...' if len(clean_content) > 200 else clean_content
                    
                    response_data = {
                        'timestamp': None,
                        'deck_name': deck_name,
                        'card_count': len(processed_cards),
                        'content_preview': content_preview,
                        'generation_config': {},
                        'cards': processed_cards,
                        'current_card_index': 0,  # 当前显示的卡片索引
                        'total_cards': len(processed_cards)
                    }
                else:
                    # 未知格式
                    response_data = {
                        'timestamp': None,
                        'deck_name': '未知牌组',
                        'card_count': 0,
                        'content_preview': '',
                        'generation_config': {},
                        'cards': []
                    }
                
                return jsonify({
                    'success': True,
                    'data': response_data
                })
                
            except Exception as e:
                self.logger.error(f"获取历史记录详情失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/history/<record_id>/download/<file_type>')
        def download_history_file(record_id, file_type):
            """下载历史记录文件"""
            try:
                # 获取绝对路径
                output_dir = Path(self.assistant.config["export"]["output_directory"]).resolve()
                file_path = output_dir / f"{record_id}.{file_type}"
                
                self.logger.info(f"下载请求: record_id={record_id}, file_type={file_type}")
                self.logger.info(f"输出目录: {output_dir}")
                self.logger.info(f"文件路径: {file_path}")
                self.logger.info(f"文件是否存在: {file_path.exists()}")
                
                if not file_path.exists():
                    self.logger.warning(f"文件不存在: {file_path}")
                    return jsonify({
                        'success': False,
                        'error': '文件不存在'
                    }), 404
                
                # 使用绝对路径发送文件，确保Windows兼容
                self.logger.info(f"发送文件: {str(output_dir)}/{file_path.name}")
                
                # 尝试使用send_file而不是send_from_directory
                from flask import send_file
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=file_path.name
                )
                
            except Exception as e:
                self.logger.error(f"下载历史记录文件失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/history/<record_id>/card/<int:card_index>')
        def get_history_card(record_id, card_index):
            """获取历史记录中的特定卡片"""
            try:
                output_dir = Path(self.assistant.config["export"]["output_directory"])
                json_file = output_dir / f"{record_id}.json"
                
                if not json_file.exists():
                    return jsonify({
                        'success': False,
                        'error': '记录不存在'
                    }), 404
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    card_data = json.load(f)
                
                # 处理卡片数据
                cards_list = []
                if isinstance(card_data, dict) and 'metadata' in card_data:
                    cards_list = card_data.get('cards', [])
                elif isinstance(card_data, list):
                    cards_list = card_data
                
                if not cards_list:
                    return jsonify({
                        'success': False,
                        'error': '没有卡片数据'
                    }), 404
                
                # 检查卡片索引是否有效
                if card_index < 1 or card_index > len(cards_list):
                    return jsonify({
                        'success': False,
                        'error': f'卡片索引无效，有效范围：1-{len(cards_list)}'
                    }), 400
                
                # 处理指定卡片
                card = cards_list[card_index - 1]  # 转换为0基索引
                processed_card = self._process_card_data(card, card_index)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'card': processed_card,
                        'current_index': card_index,
                        'total_cards': len(cards_list),
                        'has_previous': card_index > 1,
                        'has_next': card_index < len(cards_list)
                    }
                })
                
            except Exception as e:
                self.logger.error(f"获取历史记录卡片失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/history/<record_id>', methods=['DELETE'])
        def delete_history_record(record_id):
            """删除历史记录"""
            try:
                output_dir = Path(self.assistant.config["export"]["output_directory"])
                
                # 删除所有相关文件
                deleted_files = []
                for ext in ['json', 'csv', 'html', 'txt', 'apkg']:
                    file_path = output_dir / f"{record_id}.{ext}"
                    if file_path.exists():
                        file_path.unlink()
                        deleted_files.append(file_path.name)
                
                return jsonify({
                    'success': True,
                    'message': f'已删除 {len(deleted_files)} 个文件',
                    'data': {'deleted_files': deleted_files}
                })
                
            except Exception as e:
                self.logger.error(f"删除历史记录失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/test-llm', methods=['POST'])
        def test_llm():
            """测试LLM连接，输入固定或来自请求体"""
            try:
                data = request.get_json(silent=True) or {}
                prompt = data.get('prompt') or 'Hi,Who are you?'

                # 使用当前已配置的LLM客户端进行一次简单调用
                reply = self._run_async_task(
                    self.assistant.llm_manager.generate_text(prompt)
                )

                return jsonify({
                    'success': True,
                    'data': { 'reply': reply }
                })
            except Exception as e:
                err_text = str(e)
                base_url = self.assistant.config.get('llm', {}).get('base_url', '')
                
                # 处理特定错误情况
                if self._is_cloudflare_error(err_text):
                    err_text = (
                        f'请求可能被Cloudflare防护拦截（{base_url}）。请在"AI设置"中将 API 基础URL(base_url) 换为可直连、无浏览器质询的后端域名，'
                        '例如官方 OpenAI: https://api.openai.com/v1，或你的服务商提供的后端专用域名/加速地址。'
                    )
                elif self._is_html_response(err_text):
                    err_text = (
                        f'目标返回HTML页面（{base_url}）。可能是网关/反向代理错误或需要浏览器验证。'
                        '请检查 base_url 是否正确指向后端API地址，并确认网络可直连；如使用第三方服务商，请使用其后端API域名。'
                    )
                
                self.logger.error(f"API测试失败: {err_text}")
                return jsonify({
                    'success': False,
                    'error': err_text
                }), 500
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            """静态文件服务"""
            return send_from_directory('static', filename)
        
        @self.app.route('/download/<path:filename>')
        def download_file(filename):
            """文件下载服务"""
            try:
                import os
                
                # 获取Flask应用的根目录（项目根目录）
                app_root = Path(self.app.root_path).parent.parent
                output_dir = app_root / "output"
                
                # Windows路径适配：统一转换为正斜杠
                filename = filename.replace('\\', '/')
                
                # 移除可能的路径前缀
                if filename.startswith('output/'):
                    filename = filename[7:]
                elif filename.startswith('output\\'):
                    filename = filename[8:]
                
                # 确保文件名安全，防止路径遍历攻击
                filename = filename.strip('/')
                if '..' in filename or filename.startswith('/'):
                    return jsonify({
                        'success': False,
                        'error': '无效的文件名'
                    }), 400
                
                # 构建完整文件路径
                file_path = output_dir / filename
                
                self.logger.info(f"下载请求: {filename}")
                self.logger.info(f"应用根目录: {app_root}")
                self.logger.info(f"输出目录: {output_dir}")
                self.logger.info(f"文件完整路径: {file_path}")
                
                # 检查文件是否存在
                if not file_path.exists():
                    self.logger.error(f"文件不存在: {file_path}")
                    
                    # 列出output目录中的所有文件用于调试
                    if output_dir.exists():
                        files = list(output_dir.glob('*'))
                        self.logger.info(f"Output目录中的文件: {[f.name for f in files]}")
                    else:
                        self.logger.error(f"Output目录不存在: {output_dir}")
                    
                    return jsonify({
                        'success': False,
                        'error': '文件不存在'
                    }), 404
                
                # 使用绝对路径发送文件，确保Windows兼容
                return send_from_directory(
                    str(output_dir),
                    filename,
                    as_attachment=True,
                    download_name=os.path.basename(filename)
                )
                
            except Exception as e:
                self.logger.error(f"文件下载失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _register_socket_events(self):
        """注册Socket.IO事件"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接"""
            self.logger.info('客户端已连接')
            emit('status', {'message': '已连接到Anki写卡助手'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开连接"""
            self.logger.info('客户端已断开连接')
        
        @self.socketio.on('generate_cards')
        def handle_generate_cards(data):
            """处理卡片生成请求"""
            try:
                content = data.get('content', '').strip()
                
                if not content:
                    emit('generation_error', {'error': '请提供内容'})
                    return
                
                emit('generation_start', {'message': '开始生成卡片...'})
                
                # 构建生成配置
                config = GenerationConfig(
                    template_name=data.get('template', 'Quizify'),  # 默认使用Quizify模板
                    prompt_type=data.get('prompt_type', 'cloze'),   # 默认使用cloze提示词
                    card_count=data.get('card_count', self.assistant.config["generation"]["default_card_count"]),
                    custom_deck_name=data.get('deck_name'),
                    difficulty=data.get('difficulty', self.assistant.config["generation"]["default_difficulty"])
                )
                
                # 异步生成卡片
                cards = self._run_async_task(self.assistant.generate_cards(content, config))
                
                emit('generation_progress', {'message': f'已生成 {len(cards)} 张卡片'})
                
                # 导出卡片
                export_formats = data.get('export_formats', self.assistant.config["export"]["default_formats"])
                if 'json' not in export_formats:
                    export_formats.insert(0, 'json')
                export_paths = self.assistant.export_cards(cards, export_formats)
                
                # 获取摘要
                summary = self.assistant.get_export_summary(cards)
                
                serializable_cards = [c.to_dict() if hasattr(c, 'to_dict') else c for c in cards]
                emit('generation_complete', {
                    'cards': serializable_cards,
                    'export_paths': export_paths,
                    'summary': summary
                })
                
            except Exception as e:
                self.logger.error(f"生成卡片失败: {e}")
                emit('generation_error', {'error': str(e)})
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """运行Web应用"""
        self.logger.info(f"启动Web服务器: http://{host}:{port}")
        # 在调试模式下启用自动重载
        self.socketio.run(self.app, host=host, port=port, debug=debug, use_reloader=debug)
    
    def _run_async_task(self, coro):
        """运行异步任务的辅助方法"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def _is_cloudflare_error(self, error_text: str) -> bool:
        """检查是否为Cloudflare错误"""
        cf_markers = ['cf-error-details', 'Cloudflare Ray ID', '/cdn-cgi/', 'Attention Required! | Cloudflare']
        return any(marker in error_text for marker in cf_markers)
    
    def _is_html_response(self, error_text: str) -> bool:
        """检查是否为HTML响应"""
        return ('<!DOCTYPE html>' in error_text) or ('<html' in error_text.lower())

def create_app(assistant=None):
    """创建Flask应用实例"""
    if assistant is None:
        # 如果没有传入assistant，创建一个新的
        from main import AnkiCardAssistant
        assistant = AnkiCardAssistant()
    
    web_app = WebApp(assistant)
    return web_app.app

if __name__ == '__main__':
    # 直接运行时创建新的助手实例
    from main import AnkiCardAssistant
    assistant = AnkiCardAssistant()
    web_app = WebApp(assistant)
    web_app.run(debug=True)
