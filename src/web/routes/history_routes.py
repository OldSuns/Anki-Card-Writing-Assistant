"""历史记录路由模块"""

from pathlib import Path
from flask import send_file
from src.web.error_handler import handle_api_error, handle_file_error, handle_validation_error
from src.web.utils import ResponseUtils


class HistoryRoutes:
    """历史记录路由处理类"""
    
    def __init__(self, app, assistant, business_logic, history_handler):
        self.app = app
        self.assistant = assistant
        self.business_logic = business_logic
        self.history_handler = history_handler
        self.register_routes()
    
    def register_routes(self):
        """注册历史记录路由"""

        @self.app.route('/api/history')
        @handle_api_error
        def get_history():
            history_records = self.history_handler.get_history_records()
            return ResponseUtils.success_response(data={'records': history_records})

        @self.app.route('/api/history/<record_id>/detail')
        @handle_api_error
        def get_history_detail(record_id):
            detail_data = self.history_handler.get_history_detail(record_id)
            if detail_data is None:
                return ResponseUtils.error_response('记录不存在', 404)
            return ResponseUtils.success_response(data=detail_data)

        @self.app.route('/api/history/<record_id>/download/<file_type>')
        @handle_file_error
        def download_history_file(record_id, file_type):
            return self._handle_history_file_download(record_id, file_type)

        @self.app.route('/api/history/<record_id>/card/<int:card_index>')
        @handle_validation_error
        def get_history_card(record_id, card_index):
            card_data = self.history_handler.get_history_card(record_id, card_index)
            if card_data is None:
                history_file = Path(
                    self.assistant.config["export"]["output_directory"]
                ).joinpath(f"{record_id}.json")
                if not history_file.exists():
                    return ResponseUtils.error_response('记录不存在', 404)
                return ResponseUtils.error_response('卡片索引无效', 400)
            return ResponseUtils.success_response(data=card_data)

        @self.app.route('/api/history/<record_id>', methods=['DELETE'])
        @handle_api_error
        def delete_history_record(record_id):
            deleted_files = self.history_handler.delete_history_record(record_id)
            return ResponseUtils.success_response(
                message=f'已删除 {len(deleted_files)} 个文件',
                data={'deleted_files': deleted_files}
            )

    def _handle_history_file_download(self, record_id: str, file_type: str):
        """处理历史文件下载"""
        output_dir = Path(
            self.assistant.config["export"]["output_directory"]
        ).resolve()
        file_path = output_dir / f"{record_id}.{file_type}"

        self.business_logic.logger.info("下载请求: record_id=%s, file_type=%s", record_id, file_type)
        self.business_logic.logger.info("文件路径: %s", file_path)

        if not file_path.exists():
            self.business_logic.logger.warning("文件不存在: %s", file_path)
            return ResponseUtils.error_response('文件不存在或已过期', 404)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )