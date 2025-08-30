"""基础路由模块"""

from flask import render_template, send_from_directory


class BaseRoutes:
    """基础路由处理类"""
    
    def __init__(self, app):
        self.app = app
        self.register_routes()
    
    def register_routes(self):
        """注册基础路由"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/card-merge')
        def card_merge():
            return render_template('card_merge.html')

        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(
                self.app.static_folder, 'favicon.ico',
                mimetype='image/vnd.microsoft.icon'
            )