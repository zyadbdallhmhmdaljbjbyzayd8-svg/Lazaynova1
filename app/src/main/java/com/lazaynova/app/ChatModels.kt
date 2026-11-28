package com.lazaynova.app

enum class LazaynovaEngine(val id: String, val arLabel: String, val enLabel: String) {
    CHAT("chat", "محرك المحادثة", "Chat Engine"),
    RESEARCH("research", "محرك البحث", "Research Engine"),
    CODING("coding", "محرك البرمجة", "Coding Engine"),
    DOCUMENTS("documents", "محرك المستندات", "Documents Engine")
}

enum class AppLanguage(val code: String) {
    AR("ar"),
    EN("en")
}

data class ChatMessageItem(
    val id: String,
    val role: String,
    val content: String,
    val engineName: String? = null,
    val latencyMs: Long? = null,
    val isError: Boolean = false
)

data class ConversationSummary(
    val id: String,
    val title: String,
    val engineId: String = "chat"
)

data class BackendRuntimeConfig(
    val baseUrl: String = "http://127.0.0.1:8787",
    val requestTimeoutSec: Long = 45L
)

data class MainChatUiState(
    val baseUrl: String = "http://127.0.0.1:8787",
    val backendReachable: Boolean = false,
    val backendStatusText: String? = null,
    val activeEngineId: String = "chat",
    val selectedTool: LazaynovaEngine = LazaynovaEngine.CHAT,
    val language: AppLanguage = AppLanguage.AR,
    val isSending: Boolean = false,
    val errorMessage: String? = null,
    val conversations: List<ConversationSummary> = emptyList(),
    val activeConversationId: String? = null,
    val messages: List<ChatMessageItem> = emptyList()
)
