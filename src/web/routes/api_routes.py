"""API路由模块"""

from flask import request
from src.web.error_handler import handle_api_error, handle_validation_error, handle_network_error
from src.web.utils import ResponseUtils, ValidationUtils


class APIRoutes:
    """API路由处理类"""
    
    def __init__(self, app, assistant, business_logic):
        self.app = app
        self.assistant = assistant
        self.business_logic = business_logic
        self.register_routes()
    
    def register_routes(self):
        """注册所有API路由"""
        self._register_info_routes()
        self._register_generation_routes()
        self._register_settings_routes()
    
    def _register_info_routes(self):
        """注册信息获取路由"""

        @self.app.route('/api/templates')
        @handle_api_error
        def get_templates():
            templates = self.assistant.list_templates()
            return ResponseUtils.success_response(data=templates)

        @self.app.route('/api/prompts')
        @handle_api_error
        def get_prompts():
            category = request.args.get('category')
            template_name = request.args.get('template')
            prompts = self.assistant.list_prompts(
                category=category, template_name=template_name
            )
            return ResponseUtils.success_response(data=prompts)

        @self.app.route('/api/prompt-names')
        @handle_api_error
        def get_prompt_names():
            category = request.args.get('category')
            template_name = request.args.get('template')
            prompt_names = self.assistant.list_prompt_names(
                category=category, template_name=template_name
            )
            return ResponseUtils.success_response(data=prompt_names)

        @self.app.route('/api/llm-clients')
        @handle_api_error
        def get_llm_clients():
            clients = self.assistant.list_llm_clients()
            return ResponseUtils.success_response(data=clients)

    def _register_generation_routes(self):
        """注册内容生成路由"""

        @self.app.route('/api/generate', methods=['POST'])
        @handle_validation_error
        def generate_cards():
            data = request.get_json()
            content = data.get('content', '').strip()

            if ValidationUtils.is_empty_content(content):
                return ResponseUtils.error_response('请提供内容', 400)

            result = self.business_logic.process_card_generation(content, data)
            return ResponseUtils.success_response(data=result)

        @self.app.route('/api/test-llm', methods=['POST'])
        def test_llm():
            try:
                data = request.get_json(silent=True) or {}
                prompt = data.get('prompt') or 'Hi,Who are you?'

                reply = self.business_logic.async_runner.run_async_task(
                    self.assistant.llm_manager.generate_text(prompt)
                )

                return ResponseUtils.success_response(data={'reply': reply})
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                error_message = self.business_logic.handle_llm_test_error(e)
                return ResponseUtils.error_response(error_message, 500)

    def _register_settings_routes(self):
        """注册设置和配置路由"""

        @self.app.route('/api/prompt-content')
        @handle_validation_error
        def get_prompt_content():
            prompt_type = request.args.get('prompt_type')
            template_name = request.args.get('template')
            if not prompt_type:
                return ResponseUtils.error_response('请提供提示词类型', 400)

            prompt_content = self.assistant.get_prompt_content(
                prompt_type, template_name
            )
            return ResponseUtils.success_response(data={
                'content': prompt_content,
                'prompt_type': prompt_type
            })

        @self.app.route('/api/prompt-content', methods=['POST'])
        @handle_validation_error
        def save_prompt_content():
            data = request.get_json()
            prompt_type = data.get('prompt_type')
            content = data.get('content')
            template_name = data.get('template')

            if not prompt_type or ValidationUtils.is_empty_content(content):
                return ResponseUtils.error_response('请提供提示词类型和内容', 400)

            self.assistant.save_prompt_content(prompt_type, content, template_name)
            return ResponseUtils.success_response(message='提示词内容保存成功')

        @self.app.route('/api/prompt-content/reset', methods=['POST'])
        @handle_validation_error
        def reset_prompt_content():
            data = request.get_json()
            prompt_type = data.get('prompt_type')
            template_name = data.get('template')

            if not prompt_type:
                return ResponseUtils.error_response('请提供提示词类型', 400)

            original_content = self.assistant.reset_prompt_content(
                prompt_type, template_name
            )
            return ResponseUtils.success_response(
                data={
                    'content': original_content,
                    'prompt_type': prompt_type
                },
                message='提示词内容已重置为原始版本'
            )

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
            return ResponseUtils.success_response(data=settings)

        @self.app.route('/api/settings', methods=['POST'])
        @handle_validation_error
        def save_settings():
            data = request.get_json()
            if 'llm' in data:
                self.business_logic.config_processor.update_llm_settings(
                    self.assistant, data['llm']
                )

            try:
                self.assistant.save_user_settings()
            except (FileNotFoundError, PermissionError) as e:
                self.business_logic.logger.warning("持久化用户设置失败: %s", e)

            return ResponseUtils.success_response(message='设置已保存')

        @self.app.route('/api/config')
        @handle_api_error
        def get_config():
            return ResponseUtils.success_response(data={
                'generation': self.assistant.config.get("generation", {}),
                'llm': self.assistant.config.get("llm", {}),
                'export': self.assistant.config.get("export", {})
            })