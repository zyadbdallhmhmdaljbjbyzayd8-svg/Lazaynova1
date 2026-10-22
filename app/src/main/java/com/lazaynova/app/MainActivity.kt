package com.lazaynova.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

private val Page = Color(0xFFF5F8FF)
private val Ink = Color(0xFF171D50)
private val Violet = Color(0xFF713BFA)
private val Blue = Color(0xFF3287FF)
private val Muted = Color(0xFF7884AB)
private val Line = Color(0xFFE3E9F7)
private val Glow = Brush.horizontalGradient(
    listOf(Color(0xFF72E7FF), Color(0xFFB7A0FF), Color(0xFFFFB8EE))
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = android.graphics.Color.rgb(245, 248, 255)
        window.navigationBarColor = android.graphics.Color.rgb(245, 248, 255)
        window.decorView.systemUiVisibility =
            android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
            android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        setContent { LazaynovaApp() }
    }
}

private data class ChatMessage(val role: String, val text: String)

private data class ToolItem(
    val icon: String,
    val title: String,
    val subtitle: String,
    val prompt: String
)

@Composable
private fun LazaynovaApp() {
    val messages = remember {
        mutableStateListOf(
            ChatMessage(
                "assistant",
                "مرحبًا بك في Lazaynova 👋\nأنا مساعدك الذكي، جاهز لمساعدتك في أي شيء تحتاجه."
            )
        )
    }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var menuOpen by remember { mutableStateOf(false) }
    var selectedPage by remember { mutableStateOf("الرئيسية") }
    var dialogTitle by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    val tools = listOf(
        ToolItem("🖼️", "إنشاء صور", "أفكار وتصاميم", "ساعدني في إعداد وصف تفصيلي لصورة عن: "),
        ToolItem("🎬", "فيديو", "تخطيط ومشاهد", "ساعدني في كتابة فكرة وسيناريو فيديو عن: "),
        ToolItem("🎵", "موسيقى", "كلمات وأفكار", "اكتب لي كلمات أغنية عن: "),
        ToolItem("</>", "Canvas", "مساعدة برمجية", "ساعدني في إنشاء واجهة أو كود لـ: "),
        ToolItem("🔎", "Deep Research", "بحث وتحليل", "ابحث وحلّل الموضوع التالي بالتفصيل: "),
        ToolItem("🎓", "التعلم الموجّه", "شرح وتدريب", "علّمني خطوة بخطوة: "),
        ToolItem("✨", "الذكاء المخصص", "مهام متنوعة", "ساعدني في إنجاز المهمة التالية: "),
        ToolItem("📁", "المستندات", "تلخيص وصياغة", "ساعدني في كتابة أو تنظيم مستند عن: ")
    )

    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = Violet,
            secondary = Blue,
            background = Page,
            surface = Color.White,
            onSurface = Ink
        )
    ) {
        Box(
            Modifier.fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        listOf(Color(0xFFFAFCFF), Color(0xFFF0F5FF), Color.White)
                    )
                )
        ) {
            Column(Modifier.fillMaxSize()) {
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Surface(
                        onClick = { menuOpen = !menuOpen },
                        shape = RoundedCornerShape(14.dp),
                        color = Color.White,
                        border = androidx.compose.foundation.BorderStroke(1.dp, Line)
                    ) {
                        Box(Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                            if (menuOpen) {
                                Icon(Icons.Default.Close, "إغلاق القائمة", tint = Ink)
                            } else {
                                Icon(Icons.Default.Menu, "القائمة", tint = Ink)
                            }
                        }
                    }

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("✦", color = Violet, fontSize = 27.sp)
                        Spacer(Modifier.width(7.dp))
                        Text(
                            "Lazaynova",
                            color = Color(0xFF2527A6),
                            fontSize = 24.sp,
                            fontWeight = FontWeight.ExtraBold
                        )
                    }

                    Surface(
                        onClick = { dialogTitle = "حساب Lazaynova" },
                        shape = CircleShape,
                        color = Color.White,
                        border = androidx.compose.foundation.BorderStroke(1.dp, Line)
                    ) {
                        Box(Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                            Text("⋯", color = Ink, fontSize = 25.sp)
                        }
                    }
                }

                if (menuOpen) {
                    Card(
                        Modifier.fillMaxWidth().padding(horizontal = 14.dp),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        shape = RoundedCornerShape(20.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Line)
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            Text(
                                "التنقل في Lazaynova",
                                color = Ink,
                                fontSize = 17.sp,
                                fontWeight = FontWeight.Bold
                            )
                            listOf(
                                "الرئيسية", "دردشة جديدة", "المحادثات", "المكتبة",
                                "الوسائط", "المستندات", "جدولة", "الوكلاء",
                                "الذاكرة", "التكاملات", "الإعدادات", "الأمان والخصوصية"
                            ).forEach { item ->
                                Row(
                                    Modifier.fillMaxWidth()
                                        .clickable {
                                            selectedPage = item
                                            menuOpen = false
                                            when (item) {
                                                "دردشة جديدة" -> {
                                                    messages.clear()
                                                    messages.add(
                                                        ChatMessage(
                                                            "assistant",
                                                            "بدأت محادثة جديدة. كيف أستطيع مساعدتك؟"
                                                        )
                                                    )
                                                    input = ""
                                                    error = null
                                                }
                                                "الرئيسية" -> Unit
                                                else -> dialogTitle = item
                                            }
                                        }
                                        .padding(vertical = 10.dp, horizontal = 5.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("✦", color = Violet, fontSize = 17.sp)
                                    Spacer(Modifier.width(12.dp))
                                    Text(item, color = Ink, fontSize = 14.sp)
                                    Spacer(Modifier.weight(1f))
                                    Text("›", color = Muted, fontSize = 20.sp)
                                }
                                HorizontalDivider(color = Line)
                            }
                        }
                    }
                }

                LazyColumn(
                    Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(13.dp)
                ) {
                    item {
                        Spacer(Modifier.height(5.dp))
                        Column(
                            Modifier.fillMaxWidth(),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Box(
                                Modifier.size(112.dp)
                                    .shadow(18.dp, RoundedCornerShape(34.dp), ambientColor = Violet.copy(alpha = .2f))
                                    .background(Glow, RoundedCornerShape(34.dp))
                                    .padding(2.dp)
                                    .background(Color.White, RoundedCornerShape(32.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("L", fontSize = 82.sp, fontWeight = FontWeight.Black,
                                    color = Violet)
                            }
                            Spacer(Modifier.height(7.dp))
                            Text(
                                "Lazaynova",
                                fontSize = 34.sp,
                                fontWeight = FontWeight.ExtraBold,
                                style = TextStyle(
                                    brush = Brush.horizontalGradient(
                                        listOf(Color(0xFF168DFF), Violet, Color(0xFFCA4DFF))
                                    )
                                )
                            )
                            Spacer(Modifier.height(19.dp))
                            Text(
                                "مرحبًا بك في Lazaynova 👋",
                                fontSize = 23.sp,
                                fontWeight = FontWeight.Bold,
                                color = Ink,
                                textAlign = TextAlign.Center
                            )
                            Spacer(Modifier.height(9.dp))
                            Text(
                                "أنا مساعدك الذكي، جاهز لمساعدتك في أي شيء\nتخيله أو تحتاجه.",
                                fontSize = 15.sp,
                                color = Color(0xFF4D5883),
                                textAlign = TextAlign.Center,
                                lineHeight = 25.sp
                            )
                        }
                        Spacer(Modifier.height(17.dp))
                    }

                    item {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("المكونات الإضافية", color = Ink, fontSize = 18.sp,
                                fontWeight = FontWeight.Bold)
                            Spacer(Modifier.weight(1f))
                            Text("عرض الكل", color = Violet, fontSize = 12.sp,
                                modifier = Modifier.clickable { dialogTitle = "جميع الأدوات" })
                        }
                    }

                    items(tools) { tool ->
                        ToolCard(tool = tool, onClick = {
                            when (tool.title) {
                                "إنشاء صور" -> dialogTitle = "إنشاء صور"
                                "فيديو" -> dialogTitle = "الفيديو"
                                "موسيقى" -> dialogTitle = "الموسيقى"
                                "Deep Research" -> input = tool.prompt
                                "التعلم الموجّه" -> input = tool.prompt
                                "Canvas" -> input = tool.prompt
                                "المستندات" -> input = tool.prompt
                                else -> input = tool.prompt
                            }
                        })
                    }

                    item {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("المحادثة", color = Ink, fontSize = 18.sp,
                                fontWeight = FontWeight.Bold)
                            Spacer(Modifier.weight(1f))
                            Text("● محلي", color = Color(0xFF229C7A), fontSize = 12.sp)
                        }
                    }

                    items(messages) { message ->
                        val assistant = message.role == "assistant"
                        Card(
                            Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(20.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (assistant) Color.White else Color(0xFFF0ECFF)
                            ),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Line)
                        ) {
                            Column(Modifier.padding(14.dp)) {
                                Text(
                                    if (assistant) "✦ Lazaynova" else "أنت",
                                    color = Violet,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 12.sp
                                )
                                Spacer(Modifier.height(6.dp))
                                Text(message.text, color = Ink, fontSize = 14.sp, lineHeight = 23.sp)
                            }
                        }
                    }

                    if (busy) {
                        item {
                            Row(
                                Modifier.fillMaxWidth().padding(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                                Spacer(Modifier.width(10.dp))
                                Text("يجري إعداد الرد...", color = Muted, fontSize = 13.sp)
                            }
                        }
                    }

                    error?.let { problem ->
                        item {
                            Text(problem, color = Color(0xFFB3261E), fontSize = 12.sp)
                        }
                    }
                }

                Card(
                    Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 8.dp)
                        .border(2.dp, Glow, RoundedCornerShape(28.dp)),
                    shape = RoundedCornerShape(27.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 5.dp)
                ) {
                    Row(
                        Modifier.padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Surface(
                            onClick = { dialogTitle = "إضافة ملف أو صورة" },
                            shape = CircleShape,
                            color = Color(0xFFF1EDFF)
                        ) {
                            Box(Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                                Text("+", color = Violet, fontSize = 28.sp)
                            }
                        }
                        Spacer(Modifier.width(9.dp))
                        BasicTextField(
                            value = input,
                            onValueChange = { input = it },
                            modifier = Modifier.weight(1f).padding(vertical = 12.dp),
                            textStyle = TextStyle(color = Ink, fontSize = 14.sp),
                            decorationBox = { inner ->
                                Box {
                                    if (input.isEmpty()) {
                                        Text("اسأل Lazaynova...", color = Muted, fontSize = 14.sp)
                                    }
                                    inner()
                                }
                            }
                        )
                        Spacer(Modifier.width(8.dp))
                        Button(
                            enabled = input.isNotBlank() && !busy,
                            onClick = {
                                val question = input.trim()
                                if (question.isNotEmpty()) {
                                    val history = messages.map {
                                        (if (it.role == "assistant") "assistant" else "user") to it.text
                                    }.takeLast(10)
                                    messages.add(ChatMessage("user", question))
                                    input = ""
                                    busy = true
                                    error = null
                                    scope.launch {
                                        try {
                                            val answer = ApiClient.chat(question, history)
                                            messages.add(ChatMessage("assistant", answer.reply))
                                        } catch (e: Exception) {
                                            error = e.message ?: "تعذر الاتصال بالخادم."
                                            messages.add(
                                                ChatMessage(
                                                    "assistant",
                                                    "تعذر الحصول على رد. تأكد من تشغيل خادم Lazaynova."
                                                )
                                            )
                                        } finally {
                                            busy = false
                                        }
                                    }
                                }
                            },
                            modifier = Modifier.size(48.dp),
                            contentPadding = PaddingValues(0.dp),
                            shape = CircleShape,
                            colors = ButtonDefaults.buttonColors(containerColor = Violet)
                        ) {
                            Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "إرسال",
                                tint = Color.White)
                        }
                    }
                }

                Text(
                    "Lazaynova Core · الإصدار 0.1",
                    Modifier.fillMaxWidth().padding(bottom = 8.dp),
                    color = Muted,
                    fontSize = 10.sp,
                    textAlign = TextAlign.Center
                )
            }

            if (dialogTitle != null) {
                AlertDialog(
                    onDismissRequest = { dialogTitle = null },
                    containerColor = Color.White,
                    title = { Text(dialogTitle ?: "", color = Ink, fontWeight = FontWeight.Bold) },
                    text = {
                        Text(
                            when (dialogTitle) {
                                "إنشاء صور" ->
                                    "واجهة اختيار الأداة جاهزة، لكن إنشاء الصور فعليًا يحتاج إلى ربط مزوّد توليد صور."
                                "الفيديو" ->
                                    "تخطيط الفيديو وكتابة السيناريو متاحان عبر المحادثة. إنشاء ملف فيديو يحتاج إلى خدمة توليد فيديو."
                                "الموسيقى" ->
                                    "يمكنك طلب كلمات الأغاني والأفكار الموسيقية من المساعد. توليد الصوت يحتاج إلى مزوّد صوت."
                                "إضافة ملف أو صورة" ->
                                    "اختيار الملفات يحتاج إلى إضافة منتقي ملفات وصلاحية معالجة المحتوى. هذه الوظيفة لم تُربط بعد."
                                "حساب Lazaynova" ->
                                    "Lazaynova Core\nالحساب المحلي\nتسجيل الدخول والاشتراكات لم يتم ربطهما بعد."
                                else ->
                                    "هذه صفحة أولية ضمن واجهة Lazaynova. بعض الميزات تحتاج إلى تنفيذ وربط بخدمات إضافية."
                            },
                            color = Muted,
                            lineHeight = 23.sp
                        )
                    },
                    confirmButton = {
                        TextButton(onClick = { dialogTitle = null }) {
                            Text("حسنًا", color = Violet)
                        }
                    }
                )
            }
        }
    }
}

@Composable
private fun ToolCard(tool: ToolItem, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = androidx.compose.foundation.BorderStroke(1.dp, Line),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                Modifier.size(48.dp)
                    .background(Color(0xFFF0EDFF), RoundedCornerShape(15.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text(tool.icon, color = Violet, fontSize = if (tool.icon == "</>") 17.sp else 22.sp,
                    fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(tool.title, color = Ink, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Spacer(Modifier.height(3.dp))
                Text(tool.subtitle, color = Muted, fontSize = 12.sp)
            }
            Text("‹", color = Muted, fontSize = 25.sp)
        }
    }
}
