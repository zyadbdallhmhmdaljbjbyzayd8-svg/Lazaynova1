package com.lazaynova.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            LazaynovaAuthGate {
                val runtimeConfig = remember {
                    BackendRuntimeConfig(baseUrl = "http://127.0.0.1:8787")
                }
                val tokenStore = remember(applicationContext) {
                    SecureTokenStore(applicationContext)
                }
                val apiClient = remember(runtimeConfig) {
                    BackendApiClient8787(runtimeConfig)
                }
                val repository = remember(apiClient, tokenStore) {
                    ChatRepository8787(apiClient, tokenStore)
                }
                val viewModel = remember(repository, runtimeConfig) {
                    ChatViewModel8787(
                        repository = repository,
                        initialBaseUrl = runtimeConfig.baseUrl
                    )
                }

                val uiState by viewModel.uiState.collectAsState()

                MainDashboardScreen(
                    state = uiState,
                    accountEmail = repository.currentAccountEmail(),
                    onSelectTool = { tool -> viewModel.selectTool(tool) },
                    onSendMessage = { text -> viewModel.sendMessage(text) },
                    onRetryConnection = { viewModel.refreshConnectionAndConversations() },
                    onDismissError = { viewModel.dismissError() },
                    onNewChat = { viewModel.startNewConversation() },
                    onSelectConversation = { id -> viewModel.selectConversation(id) },
                    onToggleLanguage = { viewModel.toggleLanguage() },
                    onLogout = { viewModel.signOut() }
                )
            }
        }
    }
}
