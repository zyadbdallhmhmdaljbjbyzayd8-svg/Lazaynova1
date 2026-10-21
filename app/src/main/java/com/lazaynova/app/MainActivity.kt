package com.lazaynova.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

private val Ink = Color(0xFF0B1020)
private val Panel = Color(0xFF151D31)
private val Violet = Color(0xFF8B7CFF)
private val Mint = Color(0xFF54E1C1)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { LazaynovaApp() }
    }
}
private data class ChatMessage(val role: String, val text: String)

@Composable
private fun LazaynovaApp() {
    val messages = remember { mutableStateListOf(ChatMessage("assistant", "مرحبًا! أنا Lazaynova. اختر وكيلًا أو اكتب المهمة التي تريد إنجازها.")) }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    MaterialTheme(colorScheme = darkColorScheme(primary = Violet, secondary = Mint, background = Ink, surface = Panel)) {
        Surface(Modifier.fillMaxSize(), color = Ink) {
            Column(
                Modifier.fillMaxSize()
                    .background(Brush.verticalGradient(listOf(Color(0xFF17152F), Ink, Color(0xFF101B2D))))
                    .padding(horizontal = 18.dp, vertical = 14.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(48.dp).background(Violet, RoundedCornerShape(16.dp)), contentAlignment = Alignment.Center) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Color.White)
                    }
                    Column(Modifier.padding(start = 12.dp)) {
                        Text("Lazaynova", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                        Text("منصة الوكلاء الذكية", color = Mint, fontSize = 13.sp)
                    }
                }
                Spacer(Modifier.height(18.dp))
                Text("ماذا تريد أن تنجز اليوم؟", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.SemiBold)
                Text("وجّه المهمة إلى الوكيل المناسب", color = Color.LightGray, fontSize = 13.sp)
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    AgentCard("البحث", "مصادر ومعلومات", Icons.Default.Search, Modifier.weight(1f)) { input = "ابحث بعمق عن: " }
                    AgentCard("البرمجة", "كود وتصحيح", Icons.Default.Code, Modifier.weight(1f)) { input = "ساعدني في البرمجة: " }
                    AgentCard("المستندات", "تلخيص وصياغة", Icons.Default.Description, Modifier.weight(1f)) { input = "ساعدني في مستند: " }
                }
                Spacer(Modifier.height(14.dp))
                Text("المحادثة", color = Color.LightGray, fontSize = 13.sp)
                Spacer(Modifier.height(6.dp))
                LazyColumn(Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(messages) { message ->
                        val assistant = message.role == "assistant"
                        Card(
                            modifier = Modifier.fillMaxWidth(if (assistant) .94f else .88f),
                            shape = RoundedCornerShape(18.dp),
                            colors = CardDefaults.cardColors(containerColor = if (assistant) Panel else Color(0xFF2A2850))
                        ) {
                            Column(Modifier.padding(13.dp)) {
                                Text(if (assistant) "Lazaynova" else "أنت", color = if (assistant) Mint else Violet, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                Spacer(Modifier.height(4.dp))
                                Text(message.text, color = Color.White, fontSize = 14.sp)
                            }
                        }
                    }
                    if (busy) item {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = Mint)
                            Text(" الوكيل يعمل على المهمة...", color = Color.LightGray, modifier = Modifier.padding(start = 8.dp))
                        }
                    }
                }
                error?.let { Text(it, color = Color(0xFFFF9A9A), fontSize = 12.sp, modifier = Modifier.padding(vertical = 4.dp)) }
                Row(
                    Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(22.dp)).padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    BasicTextField(
                        value = input, onValueChange = { input = it },
                        modifier = Modifier.weight(1f).padding(horizontal = 10.dp, vertical = 8.dp),
                        textStyle = TextStyle(color = Color.White, fontSize = 14.sp),
                        decorationBox = { inner ->
                            Box {
                                if (input.isEmpty()) Text("اكتب مهمتك هنا...", color = Color.Gray, fontSize = 14.sp)
                                inner()
                            }
                        }
                    )
                    Button(
                        enabled = input.isNotBlank() && !busy,
                        onClick = {
                            val question = input.trim()
                            if (question.isNotEmpty()) {
                                messages.add(ChatMessage("user", question)); input = ""; busy = true; error = null
                                scope.launch {
                                    try {
                                        val history = messages.dropLast(1).map { (if (it.role == "assistant") "assistant" else "user") to it.text }
                                        val answer = ApiClient.chat(question, history)
                                        messages.add(ChatMessage("assistant", answer.reply))
                                    } catch (e: Exception) {
                                        error = e.message ?: "تعذر الاتصال بالخادم."
                                        messages.add(ChatMessage("assistant", "لم أتمكن من الوصول إلى الخادم. تأكد من نشر API وضبط API_BASE_URL."))
                                    } finally { busy = false }
                                }
                            }
                        },
                        shape = RoundedCornerShape(15.dp)
                    ) { Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "إرسال") }
                }
                Spacer(Modifier.height(6.dp))
                Text("يتطلب الرد الذكي إعداد خادم API ومزوّد ذكاء اصطناعي.", color = Color.Gray, fontSize = 11.sp, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}
@Composable
private fun AgentCard(title: String, subtitle: String, icon: ImageVector, modifier: Modifier, onClick: () -> Unit) {
    Card(modifier = modifier, onClick = onClick, shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = Panel)) {
        Column(Modifier.padding(10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, contentDescription = null, tint = Violet, modifier = Modifier.size(22.dp))
            Spacer(Modifier.height(6.dp))
            Text(title, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            Text(subtitle, color = Color.LightGray, fontSize = 10.sp, textAlign = TextAlign.Center)
        }
    }
}
