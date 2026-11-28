package com.lazaynova.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainDashboardScreen(
    state: MainChatUiState,
    accountEmail: String?,
    onSelectTool: (LazaynovaEngine) -> Unit,
    onSendMessage: (String) -> Unit,
    onRetryConnection: () -> Unit,
    onDismissError: () -> Unit,
    onNewChat: () -> Unit,
    onSelectConversation: (String) -> Unit,
    onToggleLanguage: () -> Unit,
    onLogout: () -> Unit
) {
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var draft by remember { mutableStateOf("") }
    val isAr = state.language == AppLanguage.AR

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            LazaynovaNavigationDrawer(
                state = state,
                accountEmail = accountEmail,
                onNewChat = {
                    scope.launch { drawerState.close() }
                    onNewChat()
                },
                onSelectConversation = { id ->
                    scope.launch { drawerState.close() }
                    onSelectConversation(id)
                },
                onToggleLanguage = onToggleLanguage,
                onLogout = {
                    scope.launch { drawerState.close() }
                    onLogout()
                }
            )
        }
    ) {
        Scaffold(
            containerColor = Color(0xFF070A14),
            topBar = {
                TopAppBar(
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color(0xFF0B1020),
                        titleContentColor = Color.White,
                        navigationIconContentColor = Color.White
                    ),
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = null)
                        }
                    },
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(
                                        color = if (state.backendReachable) Color(0xFF34D399) else Color(0xFFFBBF24),
                                        shape = CircleShape
                                    )
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "LAZAYNOVA",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 17.sp,
                                    color = Color.White
                                )
                                val statusLine = state.backendStatusText ?: if (state.backendReachable) {
                                    if (isAr) "متصل بالخادم 8787" else "Connected (:8787)"
                                } else {
                                    if (isAr) "غير متصل بالخادم 8787" else "Disconnected (:8787)"
                                }
                                Text(
                                    text = statusLine,
                                    fontSize = 11.sp,
                                    color = if (state.backendReachable) Color(0xFF34D399) else Color(0xFFFBBF24)
                                )
                            }
                        }
                    },
                    actions = {
                        IconButton(onClick = onRetryConnection) {
                            Icon(
                                imageVector = Icons.Default.Refresh,
                                contentDescription = if (isAr) "إعادة الفحص" else "Retry",
                                tint = Color(0xFF38BDF8)
                            )
                        }
                    }
                )
            }
        ) { innerPadding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0xFF070A14))
                    .padding(innerPadding)
                    .padding(horizontal = 12.dp, vertical = 8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    LazaynovaEngine.entries.forEach { tool ->
                        val selected = tool == state.selectedTool
                        FilterChip(
                            selected = selected,
                            onClick = { onSelectTool(tool) },
                            label = {
                                Text(
                                    text = if (isAr) tool.arLabel else tool.enLabel,
                                    fontSize = 12.sp
                                )
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                containerColor = Color(0xFF0F172A),
                                labelColor = Color(0xFFCBD5E1),
                                selectedContainerColor = Color(0xFF5B21B6),
                                selectedLabelColor = Color.White
                            )
                        )
                    }
                }

                if (state.errorMessage != null) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFF3F131C), RoundedCornerShape(10.dp))
                            .border(1.dp, Color(0xFFEF4444).copy(alpha = 0.6f), RoundedCornerShape(10.dp))
                            .clickable { onDismissError() }
                            .padding(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = state.errorMessage,
                            color = Color(0xFFFECACA),
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(state.messages, key = { it.id }) { msg ->
                        val isUser = msg.role == "user"
                        Box(
                            modifier = Modifier.fillMaxWidth(),
                            contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth(0.88f)
                                    .background(
                                        color = when {
                                            msg.isError -> Color(0xFF3B111A)
                                            isUser -> Color(0xFF3B1D7A)
                                            else -> Color(0xFF111930)
                                        },
                                        shape = RoundedCornerShape(14.dp)
                                    )
                                    .padding(12.dp)
                            ) {
                                Text(
                                    text = msg.content,
                                    color = Color.White,
                                    style = MaterialTheme.typography.bodyMedium.copy(
                                        textDirection = if (isAr) TextDirection.ContentOrRtl else TextDirection.ContentOrLtr
                                    )
                                )
                                if (!isUser && msg.engineName != null) {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    val meta = if (msg.latencyMs != null) {
                                        "${msg.engineName} • ${msg.latencyMs}ms"
                                    } else {
                                        msg.engineName
                                    }
                                    Text(
                                        text = meta,
                                        color = Color(0xFF94A3B8),
                                        fontSize = 10.sp
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                MessageComposer(
                    text = draft,
                    isSending = state.isSending,
                    language = state.language,
                    selectedTool = state.selectedTool,
                    onTextChange = { draft = it },
                    onSend = {
                        val toSend = draft.trim()
                        if (toSend.isNotEmpty()) {
                            draft = ""
                            onSendMessage(toSend)
                        }
                    }
                )
            }
        }
    }
}
