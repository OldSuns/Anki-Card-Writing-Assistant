"""
Anki写卡助手Web界面
基于Flask的Web应用
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# 添加src目录到Python路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.card_generator import GenerationConfig

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
        
        # 注册路由
        self._register_routes()
        self._register_socket_events()
    
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
                return jsonify({
                    'success': True,
                    'data': templates
                })
            except Exception as e:
                self.logger.error(f"获取模板失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/prompts')
        def get_prompts():
            """获取可用提示词"""
            try:
                category = request.args.get('category')
                prompts = self.assistant.list_prompts(category=category)
                return jsonify({
                    'success': True,
                    'data': prompts
                })
            except Exception as e:
                self.logger.error(f"获取提示词失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/prompt-names')
        def get_prompt_names():
            """获取可用提示词名称（用于显示）"""
            try:
                category = request.args.get('category')
                prompt_names = self.assistant.list_prompt_names(category=category)
                return jsonify({
                    'success': True,
                    'data': prompt_names
                })
            except Exception as e:
                self.logger.error(f"获取提示词名称失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/prompt-content')
        def get_prompt_content():
            """获取提示词内容"""
            try:
                prompt_type = request.args.get('prompt_type')
                if not prompt_type:
                    return jsonify({
                        'success': False,
                        'error': '请提供提示词类型'
                    }), 400
                
                # 获取提示词内容
                prompt_content = self.assistant.get_prompt_content(prompt_type)
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
                
                if not prompt_type or not content:
                    return jsonify({
                        'success': False,
                        'error': '请提供提示词类型和内容'
                    }), 400
                
                # 保存提示词内容
                self.assistant.save_prompt_content(prompt_type, content)
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
                
                if not prompt_type:
                    return jsonify({
                        'success': False,
                        'error': '请提供提示词类型'
                    }), 400
                
                # 重置提示词内容
                original_content = self.assistant.reset_prompt_content(prompt_type)
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
                return jsonify({
                    'success': True,
                    'data': clients
                })
            except Exception as e:
                self.logger.error(f"获取LLM客户端失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
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
                    template_name=data.get('template', self.assistant.config["generation"]["default_template"]),
                    prompt_type=data.get('prompt_type', self.assistant.config["generation"]["default_prompt_type"]),
                    llm_client="default",
                    language=data.get('language', self.assistant.config["generation"]["default_language"]),
                    difficulty=data.get('difficulty', self.assistant.config["generation"]["default_difficulty"]),
                    card_count=data.get('card_count', self.assistant.config["generation"]["default_card_count"])
                )
                
                # 异步生成卡片
                async def generate():
                    return await self.assistant.generate_cards(content, config)
                
                # 在新线程中运行异步任务
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    cards = loop.run_until_complete(generate())
                finally:
                    loop.close()
                
                # 导出卡片
                export_formats = data.get('export_formats', ['json'])
                export_paths = self.assistant.export_cards(cards, export_formats)
                
                # 获取摘要
                summary = self.assistant.get_export_summary(cards)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'cards': cards,
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
                        'max_tokens': self.assistant.config.get('llm', {}).get('max_tokens', 2000),
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
                    if 'api_key' in llm_settings:
                        self.assistant.config.setdefault('llm', {})['api_key'] = llm_settings['api_key']
                    if 'base_url' in llm_settings:
                        self.assistant.config.setdefault('llm', {})['base_url'] = llm_settings['base_url']
                    if 'model' in llm_settings:
                        self.assistant.config.setdefault('llm', {})['model'] = llm_settings['model']
                    if 'temperature' in llm_settings:
                        self.assistant.config.setdefault('llm', {})['temperature'] = float(llm_settings['temperature'])
                    if 'max_tokens' in llm_settings:
                        self.assistant.config.setdefault('llm', {})['max_tokens'] = int(llm_settings['max_tokens'])
                    if 'timeout' in llm_settings:
                        self.assistant.config.setdefault('llm', {})['timeout'] = int(llm_settings['timeout'])
                    
                    # 更新LLM客户端
                    self.assistant.update_llm_config(llm_settings)
                
                # 不再处理自动保存等界面设置
                
                # 保存到内存中的配置
                # 注意：这里不再保存到文件，因为我们要废除config目录
                
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
                template_path = data.get('template_path', None)
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
                if template_path:
                    # 使用自定义模板
                    export_path = self.assistant.export_apkg_with_custom_template(
                        cards, template_path, filename
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

        @self.app.route('/api/test-llm', methods=['POST'])
        def test_llm():
            """测试LLM连接，输入固定或来自请求体"""
            try:
                data = request.get_json(silent=True) or {}
                prompt = data.get('prompt') or 'Hi,Who are you?'

                # 使用当前已配置的LLM客户端进行一次简单调用
                async def run_test():
                    client = self.assistant.llm_manager
                    reply = await client.generate_text(prompt)
                    return reply

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    reply = loop.run_until_complete(run_test())
                finally:
                    loop.close()

                return jsonify({
                    'success': True,
                    'data': { 'reply': reply }
                })
            except Exception as e:
                err_text = str(e)
                base_url = self.assistant.config.get('llm', {}).get('base_url', '')
                # 更严格的Cloudflare判断：仅在出现典型CF标记时提示
                cf_markers = ['cf-error-details', 'Cloudflare Ray ID', '/cdn-cgi/', 'Attention Required! | Cloudflare']
                is_cf = any(m in err_text for m in cf_markers)
                if is_cf:
                    err_text = (
                        f'请求可能被Cloudflare防护拦截（{base_url}）。请在“AI设置”中将 API 基础URL(base_url) 换为可直连、无浏览器质询的后端域名，'
                        '例如官方 OpenAI: https://api.openai.com/v1，或你的服务商提供的后端专用域名/加速地址。'
                    )
                # 非CF但返回整页HTML时，给出通用指引
                elif ('<!DOCTYPE html>' in err_text) or ('<html' in err_text.lower()):
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
                # 从output目录下载文件
                output_dir = Path(self.assistant.config["export"]["output_directory"])
                file_path = output_dir / filename
                
                if not file_path.exists():
                    return jsonify({
                        'success': False,
                        'error': '文件不存在'
                    }), 404
                
                return send_from_directory(
                    output_dir, 
                    filename, 
                    as_attachment=True,
                    download_name=filename
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
                    template_name=data.get('template', self.assistant.config["generation"]["default_template"]),
                    prompt_type=data.get('prompt_type', self.assistant.config["generation"]["default_prompt_type"]),
                    llm_client="default",
                    language=data.get('language', self.assistant.config["generation"]["default_language"]),
                    difficulty=data.get('difficulty', self.assistant.config["generation"]["default_difficulty"]),
                    card_count=data.get('card_count', self.assistant.config["generation"]["default_card_count"])
                )
                
                # 异步生成卡片
                async def generate():
                    return await self.assistant.generate_cards(content, config)
                
                # 在新线程中运行异步任务
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    cards = loop.run_until_complete(generate())
                finally:
                    loop.close()
                
                emit('generation_progress', {'message': f'已生成 {len(cards)} 张卡片'})
                
                # 导出卡片
                export_formats = data.get('export_formats', ['json'])
                export_paths = self.assistant.export_cards(cards, export_formats)
                
                # 获取摘要
                summary = self.assistant.get_export_summary(cards)
                
                emit('generation_complete', {
                    'cards': cards,
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
