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
    val error: String? = null
)

class ChatViewModel : ViewModel() {

    private val repository = ChatRepository()

    private val _uiState =
        MutableStateFlow(ChatUiState())

    val uiState: StateFlow<ChatUiState> =
        _uiState.asStateFlow()

    private var nextId = 1L

    private fun engineForModel(model: String): String {
        return when (model) {
            "4LZ" -> "chat"
            "4.5LZ" -> "chat"
            "5LZ" -> "chat"
            "6LZ" -> "chat"
            "6.5LZ" -> "research"
            "7LZ" -> "agent"
            "8LZ" -> "agent"
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

    fun sendMessage(
        prompt: String,
        forcedEngine: String? = null
    ) {
        val cleanPrompt = prompt.trim()
        if (cleanPrompt.isEmpty()) return
        if (_uiState.value.isLoading) return

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
                val answer = repository.sendMessage(
                    message = cleanPrompt,
                    engineId = engine
                )

                val assistantMessage = LazaynovaMessage(
                    id = nextId++,
                    text = answer,
                    isUser = false,
                    model = model
                )

                _uiState.value = _uiState.value.copy(
                    messages = _uiState.value.messages + assistantMessage,
                    isLoading = false,
                    error = null
                )

            } catch (error: Exception) {
                val reason = error.message
                    ?: "تعذر الاتصال بالخادم المحلي."

                val errorMessage = LazaynovaMessage(
                    id = nextId++,
                    text = "تعذر تنفيذ الطلب: $reason",
                    isUser = false,
                    model = model
                )

                _uiState.value = _uiState.value.copy(
                    messages = _uiState.value.messages + errorMessage,
                    isLoading = false,
                    error = reason
                )
            }
        }
    }

    fun newChat() {
        _uiState.value = ChatUiState(
            selectedModel = _uiState.value.selectedModel
        )
    }

    fun deleteChatHistory() {
        _uiState.value = ChatUiState(
            selectedModel = _uiState.value.selectedModel
        )
    }
}
