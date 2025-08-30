"""WebSocket事件处理模块"""

from flask_socketio import emit
from src.web.utils import ValidationUtils


class SocketEvents:
    """WebSocket事件处理类"""
    
    def __init__(self, socketio, assistant, business_logic):
        self.socketio = socketio
        self.assistant = assistant
        self.business_logic = business_logic
        self.register_events()
    
    def register_events(self):
        """注册Socket.IO事件"""

        @self.socketio.on('connect')
        def handle_connect():
            self.business_logic.logger.info('客户端已连接')
            emit('status', {'message': '已连接到Anki写卡助手'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.business_logic.logger.info('客户端已断开连接')

        @self.socketio.on('generate_cards')
        def handle_generate_cards(data):
            try:
                content = data.get('content', '').strip()
                if ValidationUtils.is_empty_content(content):
                    emit('generation_error', {'error': '请提供内容'})
                    return

                emit('generation_start', {'message': '开始生成卡片...'})
                
                # 使用业务逻辑处理器生成卡片
                result = self.business_logic.process_card_generation(content, data)
                
                emit('generation_progress', {
                    'message': f'已生成 {len(result["cards"])} 张卡片'
                })

                emit('generation_complete', {
                    'cards': result['cards'],
                    'export_paths': result['export_paths'],
                    'summary': result['summary']
                })

            except (ValueError, KeyError, TypeError, RuntimeError) as e:
                self.business_logic.logger.error("生成卡片失败: %s", e)
                emit('generation_error', {'error': str(e)})