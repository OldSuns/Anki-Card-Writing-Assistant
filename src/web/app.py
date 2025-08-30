"""Web应用模块"""

import logging
import sys
import tempfile
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.file_processor import FileProcessor
from src.web.history_handler import HistoryHandler
from src.web.business_logic import BusinessLogicHandler
from src.web.routes.base_routes import BaseRoutes
from src.web.routes.api_routes import APIRoutes
from src.web.routes.file_routes import FileRoutes
from src.web.routes.history_routes import HistoryRoutes
from src.web.routes.socket_events import SocketEvents


class WebAppConstants:
    """Web应用常量"""
    SECRET_KEY = 'anki-card-assistant-secret-key'
    TEMP_DIR_NAME = "anki_card_assistant"


class WebApp:
    """Web应用类 - 简化后的主应用类"""

    def __init__(self, card_assistant):
        # 初始化Flask应用
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

        # 业务逻辑处理器
        self.business_logic = BusinessLogicHandler(self.assistant, self.logger)

        # 创建临时文件目录
        self.temp_dir = Path(tempfile.gettempdir()) / WebAppConstants.TEMP_DIR_NAME
        self.temp_dir.mkdir(exist_ok=True)

        # 注册所有路由和事件
        self._register_all_routes()

    def _register_all_routes(self):
        """注册所有路由和事件"""
        # 注册基础路由
        BaseRoutes(self.app)
        
        # 注册API路由
        APIRoutes(self.app, self.assistant, self.business_logic)
        
        # 注册文件路由
        FileRoutes(self.app, self.assistant, self.business_logic, 
                  self.file_processor, self.temp_dir)
        
        # 注册历史记录路由
        HistoryRoutes(self.app, self.assistant, self.business_logic, self.history_handler)
        
        # 注册WebSocket事件
        SocketEvents(self.socketio, self.assistant, self.business_logic)

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
