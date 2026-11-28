package com.lazaynova.app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun MessageComposer(
    text: String,
    isSending: Boolean,
    language: AppLanguage,
    selectedTool: LazaynovaEngine,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isAr = language == AppLanguage.AR
    val dir = if (isAr) LayoutDirection.Rtl else LayoutDirection.Ltr
    val textDir = if (isAr) TextDirection.ContentOrRtl else TextDirection.ContentOrLtr
    val placeholderText = if (isAr) {
        "اسأل LAZAYNOVA (${selectedTool.arLabel})..."
    } else {
        "Ask LAZAYNOVA (${selectedTool.enLabel})..."
    }

    CompositionLocalProvider(LocalLayoutDirection provides dir) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(Color(0xFF0E1528), RoundedCornerShape(16.dp))
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = onTextChange,
            enabled = !isSending,
            modifier = Modifier.weight(1f),
            textStyle = TextStyle(color = Color.White, textDirection = textDir),
            maxLines = 4,
            placeholder = {
                Text(
                    text = placeholderText,
                    color = Color(0xFF64748B)
                )
            },
            colors = OutlinedTextFieldDefaults.colors(
                focusedTextColor = Color.White,
                unfocusedTextColor = Color.White,
                disabledTextColor = Color(0xFF94A3B8),
                focusedBorderColor = Color(0xFF38BDF8),
                unfocusedBorderColor = Color(0xFF1E293B),
                cursorColor = Color(0xFF38BDF8)
            )
        )
        Spacer(modifier = Modifier.width(8.dp))
        IconButton(
            onClick = onSend,
            enabled = !isSending && text.trim().isNotEmpty(),
            modifier = Modifier
                .size(46.dp)
                .background(
                    color = if (!isSending && text.trim().isNotEmpty()) Color(0xFF2563EB) else Color(0xFF1E293B),
                    shape = RoundedCornerShape(12.dp)
                )
        ) {
            if (isSending) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = Color.White,
                    strokeWidth = 2.dp
                )
            } else {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.Send,
                    contentDescription = if (isAr) "إرسال" else "Send",
                    tint = Color.White
                )
            }
        }
    }
    }
}
