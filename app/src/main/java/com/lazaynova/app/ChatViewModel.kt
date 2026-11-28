package com.lazaynova.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class LazaynovaMessage(
    val id: Long,
    val text: String,
    val isUser: Boolean,
    val model: String = ""
)

data class ChatUiState(
    val messages: List<LazaynovaMessage> = emptyList(),
    val isLoading: Boolean = false,
    val selectedModel: String = "4LZ",
    val error: String? = null,
    val conversations: List<CloudConversation> = emptyList(),
    val activeConversationId: String? = null,
    val isLoadingHistory: Boolean = false
)

class ChatViewModel : ViewModel() {

    private val repository = ChatRepository()

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var nextId = 1L

    init {
        refreshConversations(openLatest = true)
    }

    private fun engineForModel(model: String): String {
        return when (model) {
            "4LZ", "4.5LZ", "5LZ", "6LZ" -> "chat"
            "6.5LZ" -> "research"
            "7LZ", "8LZ" -> "agent"
            else -> "chat"
        }
    }

    fun selectModel(model: String) {
        _uiState.value = _uiState.value.copy(
            selectedModel = model,
            error = null
        )
    }

    fun addLocalMessage(text: String) {
        if (text.isBlank()) return
        val current = _uiState.value
        _uiState.value = current.copy(
            messages = current.messages + LazaynovaMessage(
                id = nextId++,
                text = text,
                isUser = false
            )
        )
    }

    fun refreshConversations(openLatest: Boolean = false) {
        viewModelScope.launch {
            try {
                val conversations = repository.listConversations()
                _uiState.value = _uiState.value.copy(
                    conversations = conversations,
                    error = null
                )

                if (openLatest &&
                    _uiState.value.activeConversationId == null &&
                    conversations.isNotEmpty()
                ) {
                    openConversation(conversations.first().id)
                }
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = error.message ?: "تعذر تحميل المحادثات."
                )
            }
        }
    }

    fun openConversation(conversationId: String) {
        if (_uiState.value.isLoading) return

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoadingHistory = true,
                error = null
            )

            try {
                val messages = repository.loadMessages(conversationId)
                val mapped = messages.map { message ->
                    LazaynovaMessage(
                        id = nextId++,
                        text = message.content,
                        isUser = message.role == "user",
                        model = message.engineId
                    )
                }

                _uiState.value = _uiState.value.copy(
                    messages = mapped,
                    activeConversationId = conversationId,
                    isLoadingHistory = false,
                    error = null
                )
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoadingHistory = false,
                    error = error.message ?: "تعذر تحميل المحادثة."
                )
            }
        }
    }

    fun newChat() {
        if (_uiState.value.isLoading) return

        _uiState.value = _uiState.value.copy(
            messages = emptyList(),
            activeConversationId = null,
            error = null
        )
    }

    fun sendMessage(
        prompt: String,
        forcedEngine: String? = null
    ) {
        val cleanPrompt = prompt.trim()
        if (cleanPrompt.isEmpty() || _uiState.value.isLoading) return

        val model = _uiState.value.selectedModel
        val engine = forcedEngine ?: engineForModel(model)
        val userMessage = LazaynovaMessage(
            id = nextId++,
            text = cleanPrompt,
            isUser = true,
            model = model
        )

        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages + userMessage,
            isLoading = true,
            error = null
        )

        viewModelScope.launch {
            try {
                val result = repository.sendMessage(
                    message = cleanPrompt,
                    engineId = engine,
                    conversationId = _uiState.value.activeConversationId
                )

                val assistantMessage = LazaynovaMessage(
                    id = nextId++,
                    text = result.answer,
                    isUser = false,
                    model = model
                )

                _uiState.value = _uiState.value.copy(
                    messages = _uiState.value.messages + assistantMessage,
                    activeConversationId = result.conversationId,
                    isLoading = false,
                    error = null
                )

                refreshConversations()
            } catch (error: Exception) {
                val reason = error.message ?: "تعذر الاتصال بالخادم."
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = reason
                )
            }
        }
    }

    fun archiveConversation(conversationId: String) {
        viewModelScope.launch {
            try {
                repository.archiveConversation(conversationId)

                val current = _uiState.value
                _uiState.value = current.copy(
                    conversations = current.conversations.filterNot {
                        it.id == conversationId
                    },
                    messages = if (current.activeConversationId == conversationId) {
                        emptyList()
                    } else current.messages,
                    activeConversationId = if (
                        current.activeConversationId == conversationId
                    ) null else current.activeConversationId,
                    error = null
                )
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = error.message ?: "تعذرت أرشفة المحادثة."
                )
            }
        }
    }

    fun deleteChatHistory() {
        val id = _uiState.value.activeConversationId
        if (id == null) {
            newChat()
            return
        }
        archiveConversation(id)
    }
}
