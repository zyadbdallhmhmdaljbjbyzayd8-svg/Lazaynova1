package com.lazaynova.app

data class ChatMessage(
    val id: Long,
    val role: String,
    val text: String,
    val timestamp: Long = System.currentTimeMillis()
)

data class ChatUiState(
    val messages: List<ChatMessage> = listOf(
        ChatMessage(
            id = 1L,
            role = "assistant",
            text = "مرحباً بك في LAZAYNOVA AI.\nمساعدك الذكي المستقل، Private. Autonomous. Yours."
        )
    ),
    val input: String = "",
    val selectedEngine: String = "chat",
    val isBusy: Boolean = false,
    val error: String? = null,
    val isAuthenticated: Boolean = false,
    val isAuthenticating: Boolean = false,
    val authError: String? = null,
    val conversationId: String? = null
)

data class EngineOption(
    val id: String,
    val title: String,
    val description: String
)

val LazaynovaEngines = listOf(
    EngineOption("chat", "Lazaynova L4.5", "المحادثة العامة"),
    EngineOption("research", "Lazaynova L4", "البحث والتحليل"),
    EngineOption("coding", "Lazaynova L3", "البرمجة والمساعدة التقنية"),
    EngineOption("agent", "Lazaynova L5", "تنسيق المهام والوكلاء"),
    EngineOption("documents", "المستندات", "معالجة المستندات"),
    EngineOption("image", "الصور", "واجهة محرك الصور"),
    EngineOption("video", "الفيديو", "واجهة محرك الفيديو"),
    EngineOption("music", "الموسيقى", "واجهة محرك الموسيقى")
)
