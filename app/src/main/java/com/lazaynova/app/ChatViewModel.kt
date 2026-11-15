package com.lazaynova.app

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class ChatViewModel(
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {
    private val repository = ChatRepository()

    private val _uiState = MutableStateFlow(
        ChatUiState(
            conversationId = savedStateHandle.get<String>("conversation_id")
        )
    )
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var nextMessageId = 2L

    // Invalidates responses belonging to a conversation that has been replaced.
    private var conversationGeneration = 0L

    fun authenticate(
        username: String,
        password: String,
        register: Boolean
    ) {
        if (_uiState.value.isAuthenticating) return

        _uiState.update {
            it.copy(isAuthenticating = true, authError = null)
        }

        viewModelScope.launch {
            try {
                repository.authenticate(
                    username.trim(),
                    password,
                    register
                )

                _uiState.update {
                    it.copy(
                        isAuthenticated = true,
                        isAuthenticating = false,
                        authError = null,
                        error = null
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isAuthenticating = false,
                        isAuthenticated = false,
                        authError = e.message ?: "تعذر تسجيل الدخول."
                    )
                }
            }
        }
    }

    fun updateInput(value: String) {
        _uiState.update {
            it.copy(input = value, error = null)
        }
    }

    fun selectEngine(engine: String) {
        if (LazaynovaEngines.none { it.id == engine }) return

        _uiState.update {
            it.copy(selectedEngine = engine, error = null)
        }
    }

    fun newConversation() {
        // Any response from an older request is now stale.
        conversationGeneration++
        savedStateHandle["conversation_id"] = null

        _uiState.update { current ->
            ChatUiState(
                selectedEngine = current.selectedEngine,
                isAuthenticated = current.isAuthenticated
            )
        }

        nextMessageId = 2L
    }

    fun sendMessage() {
        val current = _uiState.value
        val question = current.input.trim()

        if (question.isEmpty() || current.isBusy) return

        if (!current.isAuthenticated) {
            _uiState.update {
                it.copy(error = "سجّل الدخول أولاً.")
            }
            return
        }

        val requestGeneration = conversationGeneration
        val requestConversationId = current.conversationId

        val userMessage = ChatMessage(
            id = nextMessageId++,
            role = "user",
            text = question
        )

        _uiState.update {
            it.copy(
                messages = it.messages + userMessage,
                input = "",
                isBusy = true,
                error = null
            )
        }

        viewModelScope.launch {
            try {
                val response = repository.sendMessage(
                    message = question,
                    conversationId = requestConversationId,
                    engine = current.selectedEngine
                )

                // Do not append a late response to a newly-created conversation.
                if (requestGeneration != conversationGeneration) {
                    return@launch
                }

                savedStateHandle["conversation_id"] = response.conversationId

                val assistantMessage = ChatMessage(
                    id = nextMessageId++,
                    role = "assistant",
                    text = response.reply
                )

                _uiState.update { latest ->
                    if (requestGeneration != conversationGeneration) {
                        latest
                    } else {
                        latest.copy(
                            conversationId = response.conversationId,
                            messages = latest.messages + assistantMessage,
                            isBusy = false,
                            error = null
                        )
                    }
                }
            } catch (e: Exception) {
                if (requestGeneration != conversationGeneration) {
                    return@launch
                }

                _uiState.update { latest ->
                    if (requestGeneration != conversationGeneration) {
                        latest
                    } else {
                        latest.copy(
                            isBusy = false,
                            error = when (e) {
                                is java.net.ConnectException ->
                                    "تعذر الوصول إلى خادم LAZAYNOVA المحلي. تحقق من تشغيل الخدمة."
                                is java.net.SocketTimeoutException ->
                                    "استغرق الخادم وقتاً أطول من المتوقع. حاول مجدداً."
                                else ->
                                    "تعذر إرسال الرسالة حالياً. تحقق من اتصال الخدمة المحلية."
                            }
                        )
                    }
                }
            }
        }
    }
}
