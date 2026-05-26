const zh = {
  // App header
  "app.title": "企业 RAG Agent",
  "app.subtitle": "基于企业知识库的可追溯问答",

  // Knowledge Base Summary
  "kb.title": "知识库",
  "kb.documents": "文档",
  "kb.pages": "页面",
  "kb.dataSize": "数据大小",
  "kb.indexed": "已索引",
  "kb.entries": "条目",
  "kb.retry": "重试",

  // RagChat
  "chat.title": "知识查询",
  "chat.newSession": "新会话",
  "chat.loadingHistory": "正在加载对话历史...",
  "chat.emptyTitle": "询问你的知识库",
  "chat.emptyDesc": "查询文档，支持完整引用追溯",
  "chat.placeholder": "输入关于文档的问题...",
  "chat.streaming": "检索并生成中...",
  "chat.stop": "停止",
  "chat.you": "你",
  "chat.agent": "Agent",
  "chat.error": "请求失败，请检查后端服务是否正常运行。",
  "chat.stopped": "⏹ *已停止生成*",

  // Preset questions
  "preset.1": "什么是 context.store，如何使用它？",
  "preset.2": "RAG 检索是如何工作的，有哪些最佳策略？",

  // Citation
  "citation.badge": "已验证来源",
  "citation.id": "ID:",
  "citation.range": "范围:",
  "citation.chars": "字符数:",
  "citation.page": "第 {n} 页",
  "citation.expand": "展开",
  "citation.collapse": "收起",
  "citation.unknownDoc": "未知文档",

  // Language toggle
  "lang.switch": "English",
} as const;

export default zh;
