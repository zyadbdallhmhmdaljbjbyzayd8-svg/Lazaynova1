package com.lazaynova.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun LazaynovaNavigationDrawer(
    state: MainChatUiState,
    accountEmail: String?,
    onNewChat: () -> Unit,
    onSelectConversation: (String) -> Unit,
    onToggleLanguage: () -> Unit,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isAr = state.language == AppLanguage.AR

    Column(
        modifier = modifier
            .fillMaxHeight()
            .width(300.dp)
            .background(Color(0xFF0B1020))
            .padding(16.dp)
    ) {
        Text(
            text = "LAZAYNOVA AI",
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = 20.sp
        )
        Text(
            text = if (isAr) "المنفذ الموحد: 8787" else "Unified Port: 8787",
            color = Color(0xFF94A3B8),
            fontSize = 12.sp
        )

        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = onNewChat,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
        ) {
            Icon(Icons.Default.Add, contentDescription = null)
            Spacer(modifier = Modifier.width(6.dp))
            Text(if (isAr) "محادثة جديدة" else "New Chat")
        }

        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = if (isAr) "المحادثات السابقة" else "Recent Chats",
            color = Color(0xFFCBD5E1),
            style = MaterialTheme.typography.titleSmall
        )
        Spacer(modifier = Modifier.height(6.dp))

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(6.dp)
        ) {
            items(state.conversations, key = { it.id }) { conv ->
                val isSelected = conv.id == state.activeConversationId
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(
                            color = if (isSelected) Color(0xFF1E293B) else Color(0xFF11182C),
                            shape = RoundedCornerShape(10.dp)
                        )
                        .clickable { onSelectConversation(conv.id) }
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = conv.title.ifBlank { if (isAr) "محادثة" else "Conversation" },
                        color = Color.White,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        fontSize = 13.sp
                    )
                }
            }
        }

        HorizontalDivider(color = Color(0xFF1E293B), modifier = Modifier.padding(vertical = 10.dp))

        if (!accountEmail.isNullOrBlank()) {
            Text(
                text = accountEmail,
                color = Color(0xFF94A3B8),
                fontSize = 12.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(modifier = Modifier.height(8.dp))
        }

        OutlinedButton(
            onClick = onToggleLanguage,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp)
        ) {
            Text(
                text = if (isAr) "Switch to English" else "التبديل إلى العربية",
                color = Color(0xFFE2E8F0)
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedButton(
            onClick = onLogout,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp)
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.Logout,
                contentDescription = null,
                tint = Color(0xFFF87171)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = if (isAr) "تسجيل الخروج" else "Sign Out",
                color = Color(0xFFF87171)
            )
        }
    }
}
