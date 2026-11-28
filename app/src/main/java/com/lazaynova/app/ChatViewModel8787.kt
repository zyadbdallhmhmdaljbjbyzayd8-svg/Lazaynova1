package com.lazaynova.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID

class ChatViewModel8787(
    private val repository: ChatRepository8787,
    initialBaseUrl: String = "http://127.0.0.1:8787"
) : ViewModel() {

    private val _uiState = MutableStateFlow(MainChatUiState(baseUrl = initialBaseUrl))
    val uiState: StateFlow<MainChatUiState> = _uiState.asStateFlow()

    init {
        refreshConnectionAndConversations()
    }

    fun refreshConnectionAndConversations() {
        viewModelScope.launch {
            when (val health = repository.probeBackend()) {
                is RepositoryOutcome.Success -> {
                    _uiState.update {
                        it.copy(
                            backendReachable = true,
                            backendStatusText = "8787 • ${health.data}",
                            errorMessage = null
                        )
                    }
                    loadConversationsInternal()
                }
                is RepositoryOutcome.Failure -> {
                    _uiState.update {
                        it.copy(
                            backendReachable = false,
                            backendStatusText = null,
                            errorMessage = health.message
                        )
                    }
                }
            }
        }
    }

    private suspend fun loadConversationsInternal() {
        when (val convRes = repository.fetchConversations()) {
            is RepositoryOutcome.Success -> {
                val list = convRes.data
                val currentActive = _uiState.value.activeConversationId
                val targetId = currentActive ?: list.firstOrNull()?.id
                _uiState.update { it.copy(conversations = list, activeConversationId = targetId) }
                if (targetId != null) {
                    loadMessagesInternal(targetId)
                }
            }
            is RepositoryOutcome.Failure -> {
                // Keep UI usable even if conversation list requires login or returns empty
                if (convRes.statusCode != 401) {
                    _uiState.update { it.copy(errorMessage = convRes.message) }
                }
            }
        }
    }

    private suspend fun loadMessagesInternal(conversationId: String) {
        when (val msgRes = repository.fetchMessages(conversationId)) {
            is RepositoryOutcome.Success -> {
                _uiState.update { it.copy(messages = msgRes.data) }
            }
            is RepositoryOutcome.Failure -> {
                if (msgRes.statusCode != 401) {
                    _uiState.update { it.copy(errorMessage = msgRes.message) }
                }
            }
        }
    }

    fun selectTool(tool: LazaynovaEngine) {
        _uiState.update {
            it.copy(
                selectedTool = tool,
                activeEngineId = tool.id,
                errorMessage = null
            )
        }
    }

    fun toggleLanguage() {
        _uiState.update {
            val nextLang = if (it.language == AppLanguage.AR) AppLanguage.EN else AppLanguage.AR
            it.copy(language = nextLang)
        }
    }

    fun dismissError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    fun startNewConversation() {
        viewModelScope.launch {
            val engineId = _uiState.value.selectedTool.id
            when (val res = repository.createConversation(engineId)) {
                is RepositoryOutcome.Success -> {
                    val created = res.data
                    _uiState.update {
                        it.copy(
                            conversations = listOf(created) + it.conversations.filterNot { c -> c.id == created.id },
                            activeConversationId = created.id,
                            messages = emptyList(),
                            errorMessage = null
                        )
                    }
                }
                is RepositoryOutcome.Failure -> {
                    _uiState.update {
                        it.copy(
                            activeConversationId = null,
                            messages = emptyList(),
                            errorMessage = res.message
                        )
                    }
                }
            }
        }
    }

    fun selectConversation(conversationId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(activeConversationId = conversationId, errorMessage = null) }
            loadMessagesInternal(conversationId)
        }
    }

    fun sendMessage(text: String) {
        val clean = text.trim()
        if (clean.isEmpty() || _uiState.value.isSending) return

        val userMsg = ChatMessageItem(
            id = "u_${UUID.randomUUID()}",
            role = "user",
            content = clean
        )
        val engineId = _uiState.value.selectedTool.id
        val convId = _uiState.value.activeConversationId

        _uiState.update {
            it.copy(
                messages = it.messages + userMsg,
                isSending = true,
                errorMessage = null
            )
        }

        viewModelScope.launch {
            when (val res = repository.sendMessage(clean, engineId, convId)) {
                is RepositoryOutcome.Success -> {
                    val payload = res.data
                    val assistantMsg = ChatMessageItem(
                        id = "a_${UUID.randomUUID()}",
                        role = "assistant",
                        content = payload.replyText,
                        engineName = payload.modelName ?: _uiState.value.selectedTool.arLabel,
                        latencyMs = payload.latencyMs,
                        isError = false
                    )
                    _uiState.update {
                        it.copy(
                            backendReachable = true,
                            activeConversationId = payload.conversationId ?: it.activeConversationId,
                            messages = it.messages + assistantMsg,
                            isSending = false
                        )
                    }
                }
                is RepositoryOutcome.Failure -> {
                    val errMsg = ChatMessageItem(
                        id = "e_${UUID.randomUUID()}",
                        role = "assistant",
                        content = res.message,
                        engineName = _uiState.value.selectedTool.arLabel,
                        isError = true
                    )
                    _uiState.update {
                        it.copy(
                            backendReachable = if (res.statusCode == -1) false else it.backendReachable,
                            messages = it.messages + errMsg,
                            isSending = false,
                            errorMessage = res.message
                        )
                    }
                }
            }
        }
    }

    fun signOut(onSignedOut: () -> Unit = {}) {
        repository.signOut()
        onSignedOut()
    }
}
