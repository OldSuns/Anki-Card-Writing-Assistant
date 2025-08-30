/**
 * 卡片合并页面的JavaScript逻辑
 */

class CardMergeApp {
    constructor() {
        this.mergeList = [];
        this.selectedHistoryRecords = [];
        this.uploadedFiles = [];
        this.templateAnalysis = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeUI();
    }

    bindEvents() {
        // 来源选择方式切换
        document.querySelectorAll('input[name="source-method"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.switchSourceMethod(e.target.value);
            });
        });

        // 模板分析区域将在添加卡片来源时自动更新

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

    async analyzeTemplates() {
        if (this.mergeList.length === 0) {
            this.hideTemplateAnalysis();
            return;
        }

        try {
            const response = await fetch('/api/merge/analyze-templates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    card_sources: this.mergeList
                })
            });

            const result = await response.json();

            if (result.success) {
                this.templateAnalysis = result.data;
                this.showTemplateAnalysis(result.data);
            } else {
                this.showError('分析模板失败: ' + result.message);
            }
        } catch (error) {
            this.showError('分析模板失败: ' + error.message);
        }
    }

    showTemplateAnalysis(analysis) {
        const area = document.getElementById('template-analysis-area');
        const content = document.getElementById('template-analysis-content');
        
        let html = '';
        
        if (analysis.has_conflict) {
            // 有冲突的情况
            html = `
                <div class="alert alert-warning">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>检测到模板冲突</h6>
                    <p class="mb-2">发现 ${analysis.total_templates} 种不同的模板，将使用主要模板：<strong>${analysis.primary_template}</strong></p>
                    <div class="small">
                        <strong>模板使用情况：</strong>
                        <ul class="mb-0 mt-1">
                            ${Object.entries(analysis.template_usage).map(([template, info]) => 
                                `<li>${template}: ${info.count} 张卡片 (来源: ${Array.from(info.sources).join(', ')})</li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            `;
        } else {
            // 无冲突的情况
            html = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle me-2"></i>模板一致</h6>
                    <p class="mb-0">所有卡片使用相同模板：<strong>${analysis.primary_template}</strong></p>
                </div>
            `;
        }
        
        content.innerHTML = html;
        area.style.display = 'block';
    }

    hideTemplateAnalysis() {
        const area = document.getElementById('template-analysis-area');
        area.style.display = 'none';
        this.templateAnalysis = null;
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

    // 检测卡片模板信息
    detectTemplate(cards) {
        if (!cards || cards.length === 0) {
            return { template: '未知模板', confidence: 'unknown' };
        }
        
        // 统计不同模板的使用情况
        const templateCounts = {};
        
        cards.forEach(card => {
            let template = '未知模板';
            
            // 检查是否有明确的模板字段
            if (card.modelName) {
                template = card.modelName;
            } else if (card.template) {
                template = card.template;
            } else if (card.fields) {
                // 根据字段推断模板类型
                const fieldNames = Object.keys(card.fields);
                if (fieldNames.includes('Text') && fieldNames.includes('Extra')) {
                    template = 'Cloze';
                } else if (fieldNames.includes('Front') && fieldNames.includes('Back')) {
                    template = 'Basic';
                } else if (fieldNames.includes('Question') && fieldNames.includes('Answer')) {
                    template = 'Basic (Question-Answer)';
                } else if (fieldNames.length >= 2) {
                    template = `自定义模板 (${fieldNames.length}字段)`;
                }
            }
            
            templateCounts[template] = (templateCounts[template] || 0) + 1;
        });
        
        // 找出最常用的模板
        const sortedTemplates = Object.entries(templateCounts)
            .sort((a, b) => b[1] - a[1]);
        
        if (sortedTemplates.length === 0) {
            return { template: '未知模板', confidence: 'unknown' };
        }
        
        const [primaryTemplate, primaryCount] = sortedTemplates[0];
        const totalCards = cards.length;
        const confidence = primaryCount === totalCards ? 'uniform' : 'mixed';
        
        return {
            template: primaryTemplate,
            confidence,
            usage: templateCounts,
            totalCards
        };
    }

    async renderHistoryList(records) {
        const historyList = document.getElementById('history-list');
        
        if (records.length === 0) {
            historyList.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-clock-rotate-left fa-3x mb-3 text-secondary"></i>
                    <h6 class="text-muted">暂无历史记录</h6>
                    <p class="small mb-0">您还没有生成过任何卡片</p>
                </div>
            `;
            return;
        }

        // 先渲染基础结构，后续异步加载模板信息
        const html = records.map(record => `
            <div class="history-record-item mb-1" data-record-id="${record.id}">
                <label class="history-record-label" for="history-${record.id}">
                    <div class="d-flex justify-content-between align-items-center py-2 px-3 border rounded position-relative">
                        <input class="form-check-input position-absolute" type="checkbox" value="${record.id}" id="history-${record.id}" style="top: 0.75rem; left: 0.75rem; margin: 0;">
                        <div class="flex-grow-1" style="margin-left: 1.5rem;">
                            <div class="d-flex align-items-center justify-content-between mb-1">
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-layer-group text-primary me-2" style="font-size: 0.8rem;"></i>
                                    <h6 class="mb-0 text-dark fw-semibold" style="font-size: 0.85rem;">${record.deck_name}</h6>
                                </div>
                                <div class="selection-indicator">
                                    <i class="fas fa-check-circle text-success d-none" style="font-size: 0.9rem;"></i>
                                    <i class="far fa-circle text-muted" style="font-size: 0.9rem;"></i>
                                </div>
                            </div>
                            <p class="card-text text-muted mb-1 lh-sm" style="max-height: 1.5em; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; font-size: 0.7rem;">
                                ${record.content_preview}
                            </p>
                            <div class="d-flex align-items-center gap-2 text-muted" style="font-size: 0.65rem;">
                                <span class="d-flex align-items-center">
                                    <i class="fas fa-calendar-alt me-1 text-info"></i>
                                    ${record.timestamp_display}
                                </span>
                                <span class="d-flex align-items-center">
                                    <i class="fas fa-cards-blank me-1 text-success"></i>
                                    ${record.card_count}张卡片
                                </span>
                                <span class="d-flex align-items-center template-loading" data-record-id="${record.id}">
                                    <i class="fas fa-spinner fa-pulse me-1 text-muted"></i>
                                    <small class="text-muted">检测中...</small>
                                </span>
                            </div>
                        </div>
                    </div>
                </label>
            </div>
        `).join('');

        historyList.innerHTML = html;

        // 绑定选择事件并添加动画效果
        this.bindHistorySelectionEvents(historyList);
        
        // 异步加载模板信息
        this.loadTemplateInfoForHistoryRecords(records);
    }

    bindHistorySelectionEvents(historyList) {
        historyList.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const recordItem = e.target.closest('.history-record-item');
                const container = recordItem.querySelector('.d-flex.border');
                const selectionIndicator = recordItem.querySelector('.selection-indicator');
                
                if (e.target.checked) {
                    // 选中状态
                    container.classList.add('border-primary');
                    container.style.background = 'rgba(74, 144, 226, 0.02)';
                    selectionIndicator.querySelector('.fas').classList.remove('d-none');
                    selectionIndicator.querySelector('.far').classList.add('d-none');
                    
                    // 添加选中动画
                    recordItem.style.transform = 'scale(1.01)';
                    setTimeout(() => {
                        recordItem.style.transform = 'scale(1)';
                    }, 150);
                } else {
                    // 未选中状态
                    container.classList.remove('border-primary');
                    container.style.background = '';
                    selectionIndicator.querySelector('.fas').classList.add('d-none');
                    selectionIndicator.querySelector('.far').classList.remove('d-none');
                }
                
                this.updateSelectedHistory();
            });
            
            // 添加悬停效果到整个label区域
            const recordItem = checkbox.closest('.history-record-item');
            const container = recordItem.querySelector('.d-flex.border');
            const label = recordItem.querySelector('.history-record-label');
            
            label.addEventListener('mouseenter', () => {
                if (!checkbox.checked) {
                    container.style.transform = 'translateY(-1px)';
                    container.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
                    container.style.borderColor = 'var(--primary-color)';
                }
            });
            
            label.addEventListener('mouseleave', () => {
                if (!checkbox.checked) {
                    container.style.transform = 'translateY(0)';
                    container.style.boxShadow = '';
                    container.style.borderColor = '';
                }
            });
        });
    }

    async loadTemplateInfoForHistoryRecords(records) {
        // 为每个记录异步加载模板信息
        for (const record of records) {
            try {
                const response = await fetch(`/api/history/${record.id}/detail`);
                const result = await response.json();
                
                if (result.success && result.data.cards) {
                    const templateInfo = this.detectTemplate(result.data.cards);
                    this.updateHistoryTemplateDisplay(record.id, templateInfo);
                } else {
                    this.updateHistoryTemplateDisplay(record.id, null);
                }
            } catch (error) {
                console.error(`加载记录 ${record.id} 的模板信息失败:`, error);
                this.updateHistoryTemplateDisplay(record.id, null);
            }
        }
    }

    updateHistoryTemplateDisplay(recordId, templateInfo) {
        const loadingElement = document.querySelector(`[data-record-id="${recordId}"].template-loading`);
        if (!loadingElement) return;
        
        if (templateInfo) {
            loadingElement.innerHTML = `
                <i class="fas fa-puzzle-piece me-1 text-warning"></i>
                <span class="template-badge badge ${templateInfo.confidence === 'uniform' ? 'bg-success' : 'bg-warning text-dark'} rounded-pill" 
                      title="${templateInfo.confidence === 'mixed' ? '混合模板' : '统一模板'}"
                      style="font-size: 0.6rem; padding: 0.15rem 0.4rem;">
                    ${templateInfo.template}
                </span>
            `;
            loadingElement.classList.remove('template-loading');
        } else {
            loadingElement.innerHTML = `
                <i class="fas fa-question-circle me-1 text-muted"></i>
                <small class="text-muted" style="font-size: 0.6rem;">未知</small>
            `;
            loadingElement.classList.remove('template-loading');
        }
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
            const wasChecked = cb.checked;
            cb.checked = !allChecked;
            
            // 触发样式更新
            if (cb.checked !== wasChecked) {
                const recordItem = cb.closest('.history-record-item');
                const container = recordItem.querySelector('.d-flex.border');
                const selectionIndicator = recordItem.querySelector('.selection-indicator');
                
                if (cb.checked) {
                    // 选中状态
                    container.classList.add('border-primary');
                    container.style.background = 'rgba(74, 144, 226, 0.02)';
                    selectionIndicator.querySelector('.fas').classList.remove('d-none');
                    selectionIndicator.querySelector('.far').classList.add('d-none');
                } else {
                    // 未选中状态
                    container.classList.remove('border-primary');
                    container.style.background = '';
                    selectionIndicator.querySelector('.fas').classList.add('d-none');
                    selectionIndicator.querySelector('.far').classList.remove('d-none');
                }
            }
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
                
                // 显示已上传文件列表
                this.renderUploadedFilesList();
                
                this.showSuccess(`成功解析文件: ${result.data.filename} (${result.data.card_count} 张卡片)`);
            } else {
                this.showError(`解析文件失败: ${result.message}`);
            }
        } catch (error) {
            this.showError(`解析文件失败: ${error.message}`);
        }
    }

    renderUploadedFilesList() {
        const container = document.getElementById('uploaded-files-container');
        const filesList = document.getElementById('uploaded-files-list');
        
        if (this.uploadedFiles.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        
        const html = this.uploadedFiles.map((file, index) => {
            // 检测模板信息
            const templateInfo = this.detectTemplate(file.cards);
            
            return `
            <div class="uploaded-file-item d-flex justify-content-between align-items-center py-2 px-2 mb-1 border rounded">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-file-alt text-primary me-2" style="font-size: 0.8rem;"></i>
                            <h6 class="mb-0 text-dark fw-semibold" style="font-size: 0.85rem;">${file.filename}</h6>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="cardMergeApp.removeUploadedFile(${index})" title="移除文件" style="padding: 0.15rem 0.4rem; font-size: 0.7rem;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="d-flex align-items-center gap-2 text-muted" style="font-size: 0.65rem;">
                        <span class="d-flex align-items-center">
                            <i class="fas fa-layer-group me-1"></i>${file.deck_name}
                        </span>
                        <span class="d-flex align-items-center">
                            <i class="fas fa-cards-blank me-1"></i>${file.card_count}张卡片
                        </span>
                        <span class="d-flex align-items-center">
                            <i class="fas fa-puzzle-piece me-1 text-warning"></i>
                            <span class="template-badge badge ${templateInfo.confidence === 'uniform' ? 'bg-success' : 'bg-warning text-dark'} rounded-pill" 
                                  title="${templateInfo.confidence === 'mixed' ? '混合模板' : '统一模板'}" 
                                  style="font-size: 0.6rem; padding: 0.15rem 0.4rem;">
                                ${templateInfo.template}
                            </span>
                        </span>
                    </div>
                </div>
            </div>
            `;
        }).join('');
        
        filesList.innerHTML = html;
    }

    removeUploadedFile(index) {
        this.uploadedFiles.splice(index, 1);
        this.renderUploadedFilesList();
        this.updateAddButtonState();
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

        // 立即更新UI和重新分析模板
        this.renderMergeList();
        this.updateMergeButtonState();
        
        // 确保模板分析在UI更新后进行
        await this.analyzeTemplates();
    }

    // 检查是否已存在重复的历史记录
    isDuplicateHistoryRecord(recordId) {
        return this.mergeList.some(item => 
            item.source_type === 'history' && item.id === `history-${recordId}`
        );
    }

    // 检查是否已存在重复的上传文件
    isDuplicateUploadFile(filename) {
        return this.mergeList.some(item => 
            item.source_type === 'upload' && item.source_name.includes(filename)
        );
    }

    // 显示重复提示信息
    showDuplicateInfo(duplicateItems, addedCount, totalCount) {
        if (duplicateItems.length > 0) {
            const duplicateNames = duplicateItems.map(item => item.name).join('、');
            const message = `跳过 ${duplicateItems.length} 个重复项目：${duplicateNames}。成功添加 ${addedCount} 个新项目到合并列表。`;
            this.showSuccess(message);
        } else if (addedCount > 0) {
            this.showSuccess(`成功添加 ${addedCount} 个项目到合并列表`);
        } else {
            this.showError('所有选中的项目都已存在于合并列表中');
        }
    }

    async addHistoryToMergeList() {
        const duplicateItems = [];
        const addedItems = [];
        const totalCount = this.selectedHistoryRecords.length;

        for (const recordId of this.selectedHistoryRecords) {
            try {
                // 检查是否重复
                if (this.isDuplicateHistoryRecord(recordId)) {
                    // 获取记录名称用于提示
                    const response = await fetch(`/api/history/${recordId}/detail`);
                    const result = await response.json();
                    if (result.success) {
                        duplicateItems.push({
                            id: recordId,
                            name: result.data.deck_name
                        });
                    }
                    continue; // 跳过重复项
                }

                const response = await fetch(`/api/history/${recordId}/detail`);
                const result = await response.json();

                if (result.success) {
                    const record = result.data;
                    const newItem = {
                        id: `history-${recordId}`,
                        source_type: 'history',
                        source_name: `历史记录: ${record.deck_name}`,
                        cards: record.cards,
                        card_count: record.card_count,
                        original_deck_name: record.deck_name
                    };
                    this.mergeList.push(newItem);
                    addedItems.push({
                        id: recordId,
                        name: record.deck_name
                    });
                }
            } catch (error) {
                console.error(`加载历史记录 ${recordId} 失败:`, error);
            }
        }

        // 显示添加结果提示
        this.showDuplicateInfo(duplicateItems, addedItems.length, totalCount);

        // 清除选择并重置样式
        this.selectedHistoryRecords = [];
        document.querySelectorAll('#history-list input[type="checkbox"]').forEach(cb => {
            const wasChecked = cb.checked;
            cb.checked = false;
            
            // 重置选择样式
            if (wasChecked) {
                const recordItem = cb.closest('.history-record-item');
                if (recordItem) {
                    const container = recordItem.querySelector('.d-flex.border');
                    const selectionIndicator = recordItem.querySelector('.selection-indicator');
                    
                    if (container) {
                        container.classList.remove('border-primary');
                        container.style.background = '';
                    }
                    if (selectionIndicator) {
                        selectionIndicator.querySelector('.fas')?.classList.add('d-none');
                        selectionIndicator.querySelector('.far')?.classList.remove('d-none');
                    }
                }
            }
        });
        document.getElementById('add-source-btn').disabled = true;
    }

    addUploadedFilesToMergeList() {
        const duplicateItems = [];
        const addedItems = [];
        const totalCount = this.uploadedFiles.length;

        this.uploadedFiles.forEach(file => {
            // 检查是否重复
            if (this.isDuplicateUploadFile(file.filename)) {
                duplicateItems.push({
                    name: file.filename
                });
                return; // 跳过重复项
            }

            const newItem = {
                id: `upload-${Date.now()}-${Math.random()}`,
                source_type: 'upload',
                source_name: `上传文件: ${file.filename}`,
                cards: file.cards,
                card_count: file.card_count,
                original_deck_name: file.deck_name
            };
            this.mergeList.push(newItem);
            addedItems.push({
                name: file.filename
            });
        });

        // 显示添加结果提示
        this.showDuplicateInfo(duplicateItems, addedItems.length, totalCount);

        // 清除上传文件
        this.uploadedFiles = [];
        this.renderUploadedFilesList(); // 更新已上传文件列表显示
        document.getElementById('merge-file-upload-input').value = '';
        document.getElementById('add-source-btn').disabled = true;
    }

    renderMergeList() {
        const mergeListContainer = document.getElementById('merge-list');
        const countBadge = document.getElementById('merge-list-count');
        const clearBtn = document.getElementById('clear-merge-list-btn');
        const emptyState = document.getElementById('merge-list-empty');

        // 更新计数
        countBadge.textContent = `${this.mergeList.length} 个来源`;
        clearBtn.disabled = this.mergeList.length === 0;

        if (this.mergeList.length === 0) {
            // 显示空状态，隐藏列表项
            emptyState.style.display = 'block';
            
            // 清空列表容器中除了空状态之外的内容
            const listItems = mergeListContainer.querySelectorAll('.list-group-item');
            listItems.forEach(item => item.remove());
            
            this.hideTemplateAnalysis();
            
            // 隐藏合并预览卡片
            const previewCard = document.getElementById('merge-preview-card');
            previewCard.classList.add('d-none');
            
            return;
        }

        // 隐藏空状态
        emptyState.style.display = 'none';

        // 生成列表项HTML
        const html = this.mergeList.map((source, index) => `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${source.source_name}</h6>
                        <p class="mb-1 text-muted small">原牌组: ${source.original_deck_name}</p>
                        <small class="text-muted">
                            <i class="fas fa-cards-blank me-1"></i>${source.card_count}张卡片
                            <i class="fas fa-tag ms-2 me-1"></i>${source.source_type === 'history' ? '历史记录' : '上传文件'}
                        </small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="cardMergeApp.removeFromMergeList(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `).join('');

        // 先清空现有的列表项，保留空状态元素
        const listItems = mergeListContainer.querySelectorAll('.list-group-item');
        listItems.forEach(item => item.remove());
        
        // 插入新的列表项到空状态元素前面
        emptyState.insertAdjacentHTML('beforebegin', html);

        // 显示合并预览
        this.showMergePreview();
    }

    removeFromMergeList(index) {
        this.mergeList.splice(index, 1);
        this.renderMergeList();
        this.updateMergeButtonState();
        
        // 重新分析模板
        if (this.mergeList.length > 0) {
            this.analyzeTemplates();
        }
    }

    clearMergeList() {
        // 清空所有相关状态
        this.mergeList = [];
        this.selectedHistoryRecords = [];
        this.uploadedFiles = [];
        this.templateAnalysis = null;
        
        // 清空历史记录选择 - 使用正确的选择器并重置样式
        document.querySelectorAll('#history-list input[type="checkbox"]:checked').forEach(checkbox => {
            checkbox.checked = false;
            
            // 重置选择样式
            const recordItem = checkbox.closest('.history-record-item');
            if (recordItem) {
                const container = recordItem.querySelector('.d-flex.border');
                const selectionIndicator = recordItem.querySelector('.selection-indicator');
                
                if (container) {
                    container.classList.remove('border-primary');
                    container.style.background = '';
                }
                if (selectionIndicator) {
                    selectionIndicator.querySelector('.fas')?.classList.add('d-none');
                    selectionIndicator.querySelector('.far')?.classList.remove('d-none');
                }
            }
        });
        
        // 清空文件上传区域 - 使用正确的ID
        const fileInput = document.getElementById('merge-file-upload-input');
        if (fileInput) {
            fileInput.value = '';
        }
        
        // 清空已上传文件列表显示
        this.renderUploadedFilesList();
        
        // 隐藏模板分析区域
        this.hideTemplateAnalysis();
        
        // 隐藏合并结果区域
        const resultCard = document.getElementById('merge-result-card');
        if (resultCard) {
            resultCard.classList.add('d-none');
        }
        
        // 更新UI
        this.renderMergeList();
        this.updateMergeButtonState();
        
        // 更新添加按钮状态
        const currentMethod = document.querySelector('input[name="source-method"]:checked')?.value || 'history';
        const addBtn = document.getElementById('add-source-btn');
        if (currentMethod === 'history') {
            addBtn.disabled = this.selectedHistoryRecords.length === 0;
        } else {
            addBtn.disabled = this.uploadedFiles.length === 0;
        }
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

        mergeBtn.disabled = this.mergeList.length === 0 || !deckName || selectedFormats.length === 0;
    }

    async startMerge() {
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
                    export_formats: selectedFormats
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
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-success mb-1">${data.merge_info.total_cards}</h4>
                    <small class="text-muted">合并卡片数</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-primary mb-1">${data.merge_info.total_sources}</h4>
                    <small class="text-muted">来源数量</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-info mb-1">${data.merge_info.merged_deck_name}</h4>
                    <small class="text-muted">牌组名称</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4 class="text-warning mb-1">${data.template_analysis?.primary_template || '未知'}</h4>
                    <small class="text-muted">使用模板</small>
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