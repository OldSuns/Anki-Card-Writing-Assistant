/**
 * 卡片合并页面的JavaScript逻辑
 */

class CardMergeApp {
    constructor() {
        this.mergeList = [];
        this.selectedHistoryRecords = [];
        this.uploadedFiles = [];
        this.selectedTemplate = '';
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeUI();
        this.loadTemplates();
    }

    bindEvents() {
        // 来源选择方式切换
        document.querySelectorAll('input[name="source-method"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.switchSourceMethod(e.target.value);
            });
        });

        // 模板选择
        document.getElementById('template-select').addEventListener('change', (e) => {
            this.selectedTemplate = e.target.value;
            this.updateMergeButtonState();
        });

        // 加载历史记录
        document.getElementById('load-history-btn').addEventListener('click', () => {
            this.loadHistoryRecords();
        });

        // 全选历史记录
        document.getElementById('select-all-history-btn').addEventListener('click', () => {
            this.selectAllHistory();
        });

        // 文件上传
        this.setupFileUpload();

        // 添加到合并列表
        document.getElementById('add-source-btn').addEventListener('click', () => {
            this.addToMergeList();
        });

        // 清空合并列表
        document.getElementById('clear-merge-list-btn').addEventListener('click', () => {
            this.clearMergeList();
        });

        // 开始合并
        document.getElementById('merge-cards-btn').addEventListener('click', () => {
            this.startMerge();
        });

        // 导出格式变化
        document.querySelectorAll('.export-format-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateMergeButtonState();
            });
        });

        // 牌组名称变化
        document.getElementById('merged-deck-name').addEventListener('input', () => {
            this.updateMergeButtonState();
        });
    }

    initializeUI() {
        this.switchSourceMethod('history');
        this.updateMergeButtonState();
    }

    async loadTemplates() {
        try {
            const response = await fetch('/api/templates');
            const result = await response.json();
            
            if (result.success) {
                this.populateTemplateSelect(result.data);
            } else {
                this.showError('加载模板失败: ' + result.error);
            }
        } catch (error) {
            this.showError('加载模板失败: ' + error.message);
        }
    }

    populateTemplateSelect(templates) {
        const select = document.getElementById('template-select');
        select.innerHTML = '<option value="">请选择模板</option>';
        
        templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template;
            option.textContent = template;
            select.appendChild(option);
        });
    }

    switchSourceMethod(method) {
        const historyArea = document.getElementById('history-source-area');
        const uploadArea = document.getElementById('upload-source-area');
        const addBtn = document.getElementById('add-source-btn');

        if (method === 'history') {
            historyArea.style.display = 'block';
            uploadArea.style.display = 'none';
            addBtn.disabled = this.selectedHistoryRecords.length === 0;
        } else {
            historyArea.style.display = 'none';
            uploadArea.style.display = 'block';
            addBtn.disabled = this.uploadedFiles.length === 0;
        }
    }

    async loadHistoryRecords() {
        const loadBtn = document.getElementById('load-history-btn');
        const selectAllBtn = document.getElementById('select-all-history-btn');
        const historyList = document.getElementById('history-list');

        // 显示加载状态
        loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>加载中...';
        loadBtn.disabled = true;

        try {
            const response = await fetch('/api/history');
            const result = await response.json();

            if (result.success) {
                this.renderHistoryList(result.data.records);
                selectAllBtn.disabled = false;
            } else {
                this.showError('加载历史记录失败: ' + result.message);
            }
        } catch (error) {
            this.showError('加载历史记录失败: ' + error.message);
        } finally {
            loadBtn.innerHTML = '<i class="fas fa-sync me-1"></i>加载历史记录';
            loadBtn.disabled = false;
        }
    }

    renderHistoryList(records) {
        const historyList = document.getElementById('history-list');
        
        if (records.length === 0) {
            historyList.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p class="mb-0">暂无历史记录</p>
                </div>
            `;
            return;
        }

        const html = records.map(record => `
            <div class="form-check border rounded p-2 mb-2">
                <input class="form-check-input" type="checkbox" value="${record.id}" id="history-${record.id}">
                <label class="form-check-label w-100" for="history-${record.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${record.deck_name}</h6>
                            <p class="mb-1 text-muted small">${record.content_preview}</p>
                            <small class="text-muted">
                                <i class="fas fa-calendar me-1"></i>${record.timestamp_display}
                                <i class="fas fa-cards-blank ms-2 me-1"></i>${record.card_count} 张卡片
                            </small>
                        </div>
                    </div>
                </label>
            </div>
        `).join('');

        historyList.innerHTML = html;

        // 绑定选择事件
        historyList.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSelectedHistory();
            });
        });
    }

    updateSelectedHistory() {
        const checkboxes = document.querySelectorAll('#history-list input[type="checkbox"]:checked');
        this.selectedHistoryRecords = Array.from(checkboxes).map(cb => cb.value);
        
        const addBtn = document.getElementById('add-source-btn');
        const currentMethod = document.querySelector('input[name="source-method"]:checked').value;
        
        if (currentMethod === 'history') {
            addBtn.disabled = this.selectedHistoryRecords.length === 0;
        }
    }

    selectAllHistory() {
        const checkboxes = document.querySelectorAll('#history-list input[type="checkbox"]');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(cb => {
            cb.checked = !allChecked;
        });
        
        this.updateSelectedHistory();
    }

    setupFileUpload() {
        const dropZone = document.getElementById('merge-file-drop-zone');
        const fileInput = document.getElementById('merge-file-upload-input');

        // 点击上传
        dropZone.addEventListener('click', () => {
            fileInput.click();
        });

        // 文件选择
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });

        // 拖拽上传
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            this.handleFileSelect(e.dataTransfer.files);
        });
    }

    async handleFileSelect(files) {
        const validFiles = Array.from(files).filter(file => 
            file.type === 'application/json' || file.name.endsWith('.json')
        );

        if (validFiles.length === 0) {
            this.showError('请选择JSON格式的卡组文件');
            return;
        }

        for (const file of validFiles) {
            await this.parseUploadedFile(file);
        }

        this.updateAddButtonState();
    }

    async parseUploadedFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/merge/parse-file', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.uploadedFiles.push({
                    filename: result.data.filename,
                    cards: result.data.cards,
                    card_count: result.data.card_count,
                    deck_name: result.data.deck_name
                });
                
                this.showSuccess(`成功解析文件: ${result.data.filename} (${result.data.card_count} 张卡片)`);
            } else {
                this.showError(`解析文件失败: ${result.message}`);
            }
        } catch (error) {
            this.showError(`解析文件失败: ${error.message}`);
        }
    }

    updateAddButtonState() {
        const addBtn = document.getElementById('add-source-btn');
        const currentMethod = document.querySelector('input[name="source-method"]:checked').value;
        
        if (currentMethod === 'upload') {
            addBtn.disabled = this.uploadedFiles.length === 0;
        }
    }

    async addToMergeList() {
        const currentMethod = document.querySelector('input[name="source-method"]:checked').value;

        if (currentMethod === 'history') {
            await this.addHistoryToMergeList();
        } else {
            this.addUploadedFilesToMergeList();
        }

        this.renderMergeList();
        this.updateMergeButtonState();
    }

    async addHistoryToMergeList() {
        for (const recordId of this.selectedHistoryRecords) {
            try {
                const response = await fetch(`/api/history/${recordId}/detail`);
                const result = await response.json();

                if (result.success) {
                    const record = result.data;
                    this.mergeList.push({
                        id: `history-${recordId}`,
                        source_type: 'history',
                        source_name: `历史记录: ${record.deck_name}`,
                        cards: record.cards,
                        card_count: record.card_count,
                        original_deck_name: record.deck_name
                    });
                }
            } catch (error) {
                console.error(`加载历史记录 ${recordId} 失败:`, error);
            }
        }

        // 清除选择
        this.selectedHistoryRecords = [];
        document.querySelectorAll('#history-list input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        document.getElementById('add-source-btn').disabled = true;
    }

    addUploadedFilesToMergeList() {
        this.uploadedFiles.forEach(file => {
            this.mergeList.push({
                id: `upload-${Date.now()}-${Math.random()}`,
                source_type: 'upload',
                source_name: `上传文件: ${file.filename}`,
                cards: file.cards,
                card_count: file.card_count,
                original_deck_name: file.deck_name
            });
        });

        // 清除上传文件
        this.uploadedFiles = [];
        document.getElementById('merge-file-upload-input').value = '';
        document.getElementById('add-source-btn').disabled = true;
    }

    renderMergeList() {
        const mergeList = document.getElementById('merge-list');
        const countBadge = document.getElementById('merge-list-count');
        const clearBtn = document.getElementById('clear-merge-list-btn');
        const emptyState = document.getElementById('merge-list-empty');

        countBadge.textContent = `${this.mergeList.length} 个来源`;
        clearBtn.disabled = this.mergeList.length === 0;

        if (this.mergeList.length === 0) {
            emptyState.style.display = 'block';
            mergeList.innerHTML = '';
            return;
        }

        emptyState.style.display = 'none';

        const html = this.mergeList.map((source, index) => `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${source.source_name}</h6>
                        <p class="mb-1 text-muted small">原牌组: ${source.original_deck_name}</p>
                        <small class="text-muted">
                            <i class="fas fa-cards-blank me-1"></i>${source.card_count} 张卡片
                            <i class="fas fa-tag ms-2 me-1"></i>${source.source_type === 'history' ? '历史记录' : '上传文件'}
                        </small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="cardMergeApp.removeFromMergeList(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `).join('');

        mergeList.innerHTML = html;

        // 显示合并预览
        this.showMergePreview();
    }

    removeFromMergeList(index) {
        this.mergeList.splice(index, 1);
        this.renderMergeList();
        this.updateMergeButtonState();
    }

    clearMergeList() {
        this.mergeList = [];
        this.renderMergeList();
        this.updateMergeButtonState();
    }

    showMergePreview() {
        const previewCard = document.getElementById('merge-preview-card');
        const previewStats = document.getElementById('merge-preview-stats');

        if (this.mergeList.length === 0) {
            previewCard.classList.add('d-none');
            return;
        }

        const totalCards = this.mergeList.reduce((sum, source) => sum + source.card_count, 0);
        const uniqueDecks = [...new Set(this.mergeList.map(source => source.original_deck_name))];

        const html = `
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-primary mb-1">${this.mergeList.length}</h4>
                    <small class="text-muted">来源数量</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-success mb-1">${totalCards}</h4>
                    <small class="text-muted">总卡片数</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-info mb-1">${uniqueDecks.length}</h4>
                    <small class="text-muted">原牌组数</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-warning mb-1">1</h4>
                    <small class="text-muted">合并后牌组</small>
                </div>
            </div>
        `;

        previewStats.innerHTML = html;
        previewCard.classList.remove('d-none');
    }

    updateMergeButtonState() {
        const mergeBtn = document.getElementById('merge-cards-btn');
        const deckName = document.getElementById('merged-deck-name').value.trim();
        const selectedFormats = document.querySelectorAll('.export-format-checkbox:checked');

        mergeBtn.disabled = this.mergeList.length === 0 || !deckName || selectedFormats.length === 0 || !this.selectedTemplate;
    }

    async startMerge() {
        if (!this.selectedTemplate) {
            this.showError('请选择卡片模板');
            return;
        }

        const mergeBtn = document.getElementById('merge-cards-btn');
        const deckName = document.getElementById('merged-deck-name').value.trim();
        const selectedFormats = Array.from(document.querySelectorAll('.export-format-checkbox:checked'))
            .map(cb => cb.value);

        // 显示加载状态
        const btnContent = mergeBtn.querySelector('.btn-content');
        const btnLoading = mergeBtn.querySelector('.btn-loading');
        btnContent.classList.add('d-none');
        btnLoading.classList.remove('d-none');
        mergeBtn.disabled = true;

        try {
            const response = await fetch('/api/merge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    card_sources: this.mergeList,
                    merged_deck_name: deckName,
                    export_formats: selectedFormats,
                    template: this.selectedTemplate
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showMergeResult(result.data);
                this.showSuccess(`成功合并 ${result.data.merge_info.total_cards} 张卡片！`);
            } else {
                this.showError('合并失败: ' + result.message);
            }
        } catch (error) {
            this.showError('合并失败: ' + error.message);
        } finally {
            // 恢复按钮状态
            btnContent.classList.remove('d-none');
            btnLoading.classList.add('d-none');
            mergeBtn.disabled = false;
        }
    }

    showMergeResult(data) {
        const resultCard = document.getElementById('merge-result-card');
        const resultSummary = document.getElementById('merge-result-summary');
        const exportLinks = document.getElementById('merge-export-links');

        // 显示摘要
        const summaryHtml = `
            <div class="col-md-4">
                <div class="text-center">
                    <h4 class="text-success mb-1">${data.merge_info.total_cards}</h4>
                    <small class="text-muted">合并卡片数</small>
                </div>
            </div>
            <div class="col-md-4">
                <div class="text-center">
                    <h4 class="text-primary mb-1">${data.merge_info.total_sources}</h4>
                    <small class="text-muted">来源数量</small>
                </div>
            </div>
            <div class="col-md-4">
                <div class="text-center">
                    <h4 class="text-info mb-1">${data.merge_info.merged_deck_name}</h4>
                    <small class="text-muted">牌组名称</small>
                </div>
            </div>
        `;

        resultSummary.innerHTML = summaryHtml;

        // 显示导出链接
        const exportHtml = Object.entries(data.export_paths).map(([format, path]) => {
            const icons = {
                json: 'fas fa-code',
                html: 'fas fa-code',
                csv: 'fas fa-table',
                txt: 'fas fa-file-alt',
                apkg: 'fas fa-file-export'
            };

            return `
                <div class="col-md-6 mb-2">
                    <a href="/download/${path}" class="btn btn-outline-primary btn-sm w-100" download>
                        <i class="${icons[format] || 'fas fa-download'} me-2"></i>
                        下载 ${format.toUpperCase()}
                    </a>
                </div>
            `;
        }).join('');

        exportLinks.innerHTML = `<div class="row">${exportHtml}</div>`;

        resultCard.classList.remove('d-none');
        
        // 滚动到结果区域
        resultCard.scrollIntoView({ behavior: 'smooth' });
    }

    showError(message) {
        const toast = document.getElementById('error-toast');
        const toastBody = document.getElementById('error-toast-body');
        toastBody.textContent = message;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    showSuccess(message) {
        const toast = document.getElementById('success-toast');
        const toastBody = document.getElementById('success-toast-body');
        toastBody.textContent = message;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// 初始化应用
let cardMergeApp;
document.addEventListener('DOMContentLoaded', function() {
    cardMergeApp = new CardMergeApp();
});

// 历史记录选择模态框功能
document.addEventListener('DOMContentLoaded', function() {
    // 设置按钮 - 显示简化提示
    document.getElementById('settings-btn').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('settings-modal'));
        modal.show();
    });

    // 历史记录按钮 - 显示简化提示  
    document.getElementById('history-btn').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('history-modal'));
        modal.show();
    });
});