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
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Checklist
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Hub
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

private val Page = Color(0xFFF7F9FF)
private val Ink = Color(0xFF17245F)
private val Violet = Color(0xFF6725F5)
private val Blue = Color(0xFF287DFF)
private val Muted = Color(0xFF7584AE)
private val Line = Color(0xFFE0E8F7)
private val Glow = Brush.horizontalGradient(
    listOf(Color(0xFF5DE8FF), Color(0xFF9F9CFF), Color(0xFFFFB8EC), Color(0xFF5DE8FF))
)
private val LogoGradient = Brush.linearGradient(
    listOf(Color(0xFF1A41FF), Color(0xFF9B35FF), Color(0xFF42E9FF))
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = android.graphics.Color.rgb(247, 249, 255)
        window.navigationBarColor = android.graphics.Color.rgb(247, 249, 255)
        window.decorView.systemUiVisibility =
            android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
                android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        setContent {
            CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
                LazaynovaApp()
            }
        }
    }
}

private data class ChatMessage(val role: String, val text: String)
private data class UiTool(
    val title: String,
    val subtitle: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val prompt: String
)

@Composable
private fun LazaynovaApp() {
    val welcome = "مرحبًا بك في Lazaynova 👋\nأنا مساعدك الذكي، جاهز لمساعدتك في أي شيء تحتاجه."
    val messages = remember { mutableStateListOf(ChatMessage("assistant", welcome)) }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var showNavigation by remember { mutableStateOf(false) }
    var showTools by remember { mutableStateOf(false) }
    var dialogTitle by remember { mutableStateOf<String?>(null) }
    var selectedEngine by remember { mutableStateOf("chat") }
    val scope = rememberCoroutineScope()

    val tools = listOf(
        UiTool("رفع الصور", "إرفاق صورة بالمحادثة", Icons.Default.Image, "أريد العمل على صورة."),
        UiTool("الكاميرا", "التقاط صورة", Icons.Default.CameraAlt, "أريد استخدام الكاميرا."),
        UiTool("رفع الملفات", "ملفات ومستندات", Icons.Default.AttachFile, "أريد العمل على ملف مرفق."),
        UiTool("إدارة المهام", "إنشاء المهام ومتابعتها", Icons.Default.Checklist, "ساعدني في إنشاء خطة مهام ومتابعتها: "),
        UiTool("توليد الموسيقى", "أفكار وموسيقى", Icons.Default.MusicNote, "ساعدني في إنشاء موسيقى عن: "),
        UiTool("توليد الفيديو", "الفكرة والسيناريو والفيديو", Icons.Default.VideoLibrary, "ساعدني في إنشاء فيديو عن: "),
        UiTool("البحث العميق", "بحث وتحليل متقدم", Icons.Default.Search, "ابحث وحلّل الموضوع التالي بالتفصيل: "),
        UiTool("التعلّم الموجّه", "شرح خطوة بخطوة", Icons.Default.School, "علّمني خطوة بخطوة: "),
        UiTool("التحكم بالهاتف", "أوامر الهاتف المسموح بها", Icons.Default.SmartToy, "أريد المساعدة في تنفيذ إجراء على هاتفي: "),
        UiTool("إنشاء التطبيقات", "برمجة واختبار ونشر", Icons.Default.AutoAwesome, "أريد إنشاء تطبيق. الفكرة هي: "),
        UiTool("المزيد من الأدوات", "ميزات Lazaynova", Icons.Default.Hub, "ساعدني في اختيار أداة Lazaynova المناسبة لمهمتي: ")
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
            Modifier.fillMaxSize().background(
                Brush.verticalGradient(listOf(Color(0xFFF8FBFF), Color(0xFFF1F5FF), Color.White))
            )
        ) {
            Column(Modifier.fillMaxSize()) {
                    Header(
                        selectedEngine = selectedEngine,
                        onEngineSelected = { selectedEngine = it },
                        onMenu = { showNavigation = !showNavigation },
                        onNewChat = {
                            messages.clear()
                            messages.add(ChatMessage("assistant", welcome))
                            input = ""
                            error = null
                        }
                    )

                    val hasConversation = messages.any { it.role == "user" }
                    if (!hasConversation) {
                        Box(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 24.dp)) {
                            Column(
                                Modifier.align(Alignment.Center).fillMaxWidth(),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                LogoMark(76.dp)
                                Spacer(Modifier.height(18.dp))
                                Text(
                                    "كيف أستطيع مساعدتك؟",
                                    color = Ink,
                                    fontSize = 25.sp,
                                    fontWeight = FontWeight.Bold,
                                    textAlign = TextAlign.Center
                                )
                                Spacer(Modifier.height(8.dp))
                                Text(
                                    "اسأل، أنشئ، تعلّم، أو اطلب تنفيذ مهمة.",
                                    color = Muted,
                                    fontSize = 14.sp,
                                    textAlign = TextAlign.Center,
                                    lineHeight = 23.sp
                                )
                            }
                        }
                    } else {
                        LazyColumn(
                            Modifier.weight(1f).fillMaxWidth(),
                            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 14.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(messages) { message ->
                                val assistant = message.role == "assistant"
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = if (assistant) Arrangement.Start else Arrangement.End
                                ) {
                                    Card(
                                        Modifier.fillMaxWidth(.94f),
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
                                            Spacer(Modifier.height(7.dp))
                                            Text(message.text, color = Ink, fontSize = 15.sp, lineHeight = 25.sp)
                                        }
                                    }
                                }
                            }
                            if (busy) {
                                item {
                                    Row(
                                        Modifier.fillMaxWidth().padding(8.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                                        Spacer(Modifier.width(10.dp))
                                        Text("يجري إعداد الرد...", color = Muted)
                                    }
                                }
                            }
                            error?.let { problem ->
                                item { Text(problem, color = Color(0xFFB3261E), fontSize = 12.sp) }
                            }
                        }
                    }

                    ChatComposer(
                        value = input,
                        onValueChange = { input = it },
                        enabled = !busy,
                        onAdd = { showTools = true },
                        onVoice = { dialogTitle = "المحادثة الصوتية" },
                        onCall = { dialogTitle = "المكالمة الصوتية" },
                        onSend = {
                            val question = input.trim()
                            if (question.isNotEmpty() && !busy) {
                                val history = messages.map {
                                    (if (it.role == "assistant") "assistant" else "user") to it.text
                                }.takeLast(10)
                                messages.add(ChatMessage("user", question))
                                input = ""
                                busy = true
                                error = null
                                scope.launch {
                                    try {
                                        val answer = ApiClient.chat(question, history, selectedEngine)
                                        messages.add(ChatMessage("assistant", answer.reply))
                                    } catch (e: Exception) {
                                        error = e.message ?: "تعذر الاتصال بالخادم."
                                        messages.add(ChatMessage("assistant", "تعذر الحصول على رد. تأكد من تشغيل خادم Lazaynova."))
                                    } finally {
                                        busy = false
                                    }
                                }
                            }
                        }
                    )
                    Text(
                        "Lazaynova Core · الإصدار 0.1",
                        Modifier.fillMaxWidth().padding(vertical = 5.dp),
                        color = Muted,
                        fontSize = 10.sp,
                        textAlign = TextAlign.Center
                    )
            }

            if (showNavigation) {
                Box(
                    Modifier.fillMaxSize()
                        .background(Color(0x550B1230))
                        .clickable { showNavigation = false }
                )
                NavigationPanel(
                    onClose = { showNavigation = false },
                    onNewChat = {
                        messages.clear()
                        messages.add(ChatMessage("assistant", welcome))
                        input = ""
                        error = null
                        showNavigation = false
                    },
                    onItem = { item ->
                        showNavigation = false
                        dialogTitle = item
                    },
                    modifier = Modifier.align(Alignment.CenterStart)
                        .fillMaxHeight().fillMaxWidth(.84f)
                )
            }

            if (showTools) {
                AlertDialog(
                    onDismissRequest = { showTools = false },
                    containerColor = Color.White,
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("أدوات Lazaynova", Modifier.weight(1f), color = Ink, fontWeight = FontWeight.Bold)
                            IconButton(onClick = { showTools = false }) {
                                Icon(Icons.Default.Close, contentDescription = "إغلاق", tint = Muted)
                            }
                        }
                    },
                    text = {
                        LazyColumn(
                            modifier = Modifier.heightIn(max = 440.dp),
                            verticalArrangement = Arrangement.spacedBy(7.dp)
                        ) {
                            items(tools.chunked(2)) { pair ->
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    pair.forEach { tool ->
                                        ToolTile(
                                            tool = tool,
                                            modifier = Modifier.weight(1f),
                                            onClick = {
                                                showTools = false
                                                when (tool.title) {
                                                    "رفع الصور", "الكاميرا", "رفع الملفات" -> dialogTitle = tool.title
                                                    "التحكم بالهاتف" -> dialogTitle = "التحكم بالهاتف"
                                                    else -> input = tool.prompt
                                                }
                                            }
                                        )
                                    }
                                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                                }
                            }
                        }
                    },
                    confirmButton = {
                        TextButton(onClick = { showTools = false }) { Text("إغلاق", color = Violet) }
                    }
                )
            }

            if (dialogTitle != null) {
                AlertDialog(
                    onDismissRequest = { dialogTitle = null },
                    containerColor = Color.White,
                    title = { Text(dialogTitle.orEmpty(), color = Ink, fontWeight = FontWeight.Bold) },
                    text = {
                        Text(
                            when (dialogTitle) {
                                "المكالمة الصوتية", "المحادثة الصوتية" ->
                                    "مكان المكالمة الصوتية جاهز في الواجهة. ربط الصوت المباشر يحتاج إلى تنفيذ خدمة الصوت."
                                "رفع الصور" -> "ربط منتقي الصور ومعالجة الصورة سيكون في مهمة مستقلة."
                                "الكاميرا" -> "فتح الكاميرا والتقاط الصور يحتاج إلى ربط واجهة كاميرا وأذونات Android."
                                "رفع الملفات" -> "ربط منتقي الملفات وإرسال محتواها إلى المحادثة سيكون في مهمة مستقلة."
                                "التحكم بالهاتف" -> "تنفيذ أوامر الهاتف يحتاج إلى صلاحيات Android وخدمة تنفيذ آمنة. لن تُنفّذ الأوامر قبل منح الإذن."
                                "المحادثات" -> "حفظ المحادثات واستعادتها بعد إغلاق التطبيق سيكون مهمة مستقلة تالية."
                                else -> "هذه صفحة أولية ضمن واجهة Lazaynova. سنربط وظيفتها الفعلية في مهمة مستقلة."
                            },
                            color = Muted,
                            lineHeight = 23.sp
                        )
                    },
                    confirmButton = {
                        TextButton(onClick = { dialogTitle = null }) { Text("حسنًا", color = Violet) }
                    }
                )
            }
        }
    }
}

@Composable
private fun Header(
    selectedEngine: String,
    onEngineSelected: (String) -> Unit,
    onMenu: () -> Unit,
    onNewChat: () -> Unit
) {
    var engineMenu by remember { mutableStateOf(false) }
    var moreMenu by remember { mutableStateOf(false) }
    val engines = listOf(
        "chat" to "Lazaynova 4.5",
        "research" to "البحث والتحليل",
        "coding" to "البرمجة",
        "documents" to "المستندات",
        "image" to "الصور",
        "video" to "الفيديو",
        "music" to "الموسيقى",
        "agent" to "فريق الوكلاء"
    )
    val label = engines.firstOrNull { it.first == selectedEngine }?.second
        ?: "Lazaynova 4.5"

    Row(
        Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Surface(
            onClick = onMenu,
            shape = RoundedCornerShape(13.dp),
            color = Color.White,
            border = androidx.compose.foundation.BorderStroke(1.dp, Line)
        ) {
            Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Menu, contentDescription = "القائمة الجانبية", tint = Ink)
            }
        }

        Spacer(Modifier.weight(1f))

        Box {
            Surface(
                onClick = { engineMenu = true },
                shape = RoundedCornerShape(14.dp),
                color = Color.White,
                border = androidx.compose.foundation.BorderStroke(1.dp, Line)
            ) {
                Row(
                    Modifier.padding(horizontal = 10.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(label, color = Color(0xFF2527A6), fontSize = 14.sp,
                        fontWeight = FontWeight.Bold, maxLines = 1)
                    Text("⌄", color = Violet, fontSize = 20.sp)
                }
            }
            DropdownMenu(
                expanded = engineMenu,
                onDismissRequest = { engineMenu = false }
            ) {
                engines.forEach { (id, name) ->
                    DropdownMenuItem(
                        text = { Text(name, color = if (id == selectedEngine) Violet else Ink) },
                        onClick = {
                            onEngineSelected(id)
                            engineMenu = false
                        }
                    )
                }
            }
        }

        Spacer(Modifier.weight(1f))

        Box {
            Surface(
                onClick = { moreMenu = true },
                shape = RoundedCornerShape(13.dp),
                color = Color.White,
                border = androidx.compose.foundation.BorderStroke(1.dp, Line)
            ) {
                Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) {
                    Text("⋮", color = Ink, fontSize = 25.sp, fontWeight = FontWeight.Bold)
                }
            }
            DropdownMenu(
                expanded = moreMenu,
                onDismissRequest = { moreMenu = false }
            ) {
                DropdownMenuItem(
                    text = { Text("محادثة جديدة") },
                    leadingIcon = { Icon(Icons.Default.AutoAwesome, contentDescription = null) },
                    onClick = {
                        moreMenu = false
                        onNewChat()
                    }
                )
            }
        }
    }
}
@Composable
private fun NavigationPanel(
    onClose: () -> Unit,
    onNewChat: () -> Unit,
    onItem: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier.background(Color(0xFFF8FAFF)).border(1.dp, Line)
            .verticalScroll(rememberScrollState()).padding(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LogoMark(38.dp)
            Spacer(Modifier.width(8.dp))
            Text("Lazaynova", color = Color(0xFF2527A6), fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
            Spacer(Modifier.weight(1f))
            IconButton(onClick = onClose) { Icon(Icons.Default.Close, contentDescription = "إغلاق القائمة") }
        }
        Spacer(Modifier.height(12.dp))
        NavigationItem("محادثة جديدة", Icons.Default.AutoAwesome, onClick = onNewChat)
        NavigationItem("المحادثات", Icons.Default.History) { onItem("المحادثات") }
        HorizontalDivider(Modifier.padding(vertical = 9.dp), color = Line)
        Text("الوكلاء والإدارة", color = Muted, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        NavigationItem("الوكلاء", Icons.Default.Hub) { onItem("الوكلاء") }
        NavigationItem("إعدادات الوكلاء", Icons.Default.SmartToy) { onItem("إعدادات الوكلاء") }
        NavigationItem("الذاكرة", Icons.Default.Memory) { onItem("الذاكرة") }
        NavigationItem("التكاملات", Icons.Default.Link) { onItem("التكاملات") }
        NavigationItem("الأمان والخصوصية", Icons.Default.Security) { onItem("الأمان والخصوصية") }
        NavigationItem("السجلات والتحليلات", Icons.Default.BarChart) { onItem("السجلات والتحليلات") }
        HorizontalDivider(Modifier.padding(vertical = 9.dp), color = Line)
        Text("الإعدادات", color = Muted, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        NavigationItem("المظهر", Icons.Default.Settings) { onItem("المظهر") }
        NavigationItem("اللغة", Icons.Default.Language) { onItem("اللغة") }
        NavigationItem("صوت الوكيل", Icons.Default.GraphicEq) { onItem("صوت الوكيل") }
        NavigationItem("الإشعارات", Icons.Default.Notifications) { onItem("الإشعارات") }
        NavigationItem("المكتبة والملفات", Icons.Default.Folder) { onItem("المكتبة والملفات") }
        Spacer(Modifier.height(12.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = Color.White),
            border = androidx.compose.foundation.BorderStroke(1.dp, Line),
            shape = RoundedCornerShape(16.dp)
        ) {
            Row(Modifier.fillMaxWidth().padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                LogoMark(34.dp)
                Spacer(Modifier.width(8.dp))
                Column {
                    Text("Lazaynova Core", color = Ink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text("المساعد الرئيسي", color = Muted, fontSize = 10.sp)
                }
            }
        }
    }
}

@Composable
private fun NavigationItem(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 2.dp)
            .clickable(onClick = onClick)
            .background(Color.Transparent, RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = title, tint = Violet, modifier = Modifier.size(21.dp))
        Spacer(Modifier.width(12.dp))
        Text(title, color = Ink, fontSize = 13.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun LogoMark(size: androidx.compose.ui.unit.Dp) {
    Box(
        Modifier.size(size)
            .shadow(8.dp, RoundedCornerShape(size * .24f), ambientColor = Violet.copy(alpha = .2f))
            .background(Glow, RoundedCornerShape(size * .24f))
            .padding(1.5.dp)
            .background(Color.White, RoundedCornerShape(size * .24f)),
        contentAlignment = Alignment.Center
    ) {
        Text(
            "L",
            fontSize = (size.value * .72f).sp,
            fontWeight = FontWeight.Black,
            style = TextStyle(brush = LogoGradient)
        )
    }
}

@Composable
private fun ToolTile(tool: UiTool, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = modifier.heightIn(min = 88.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFBFCFF)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Line)
    ) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 5.dp, vertical = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(tool.icon, contentDescription = tool.title, tint = Violet, modifier = Modifier.size(25.dp))
            Spacer(Modifier.height(7.dp))
            Text(
                tool.title,
                color = Ink,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center,
                lineHeight = 15.sp
            )
        }
    }
}

@Composable
private fun ChatComposer(
    value: String,
    onValueChange: (String) -> Unit,
    enabled: Boolean,
    onAdd: () -> Unit,
    onVoice: () -> Unit,
    onCall: () -> Unit,
    onSend: () -> Unit
) {
    Card(
        Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 5.dp)
            .shadow(9.dp, RoundedCornerShape(28.dp), ambientColor = Violet.copy(alpha = .12f))
            .border(1.5.dp, Glow, RoundedCornerShape(28.dp)),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(Modifier.padding(7.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(onClick = onAdd, shape = CircleShape, color = Color(0xFFF1EDFF)) {
                Box(Modifier.size(40.dp), contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Add, contentDescription = "الأدوات والإضافات", tint = Violet)
                }
            }
            Spacer(Modifier.width(6.dp))
            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.weight(1f).padding(vertical = 12.dp),
                textStyle = TextStyle(color = Ink, fontSize = 15.sp),
                decorationBox = { inner ->
                    Box {
                        if (value.isEmpty()) Text("اسأل Lazaynova...", color = Muted, fontSize = 14.sp)
                        inner()
                    }
                }
            )
            IconButton(onClick = onVoice, enabled = enabled, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Mic, contentDescription = "المحادثة الصوتية", tint = Violet)
            }
            IconButton(onClick = onCall, enabled = enabled, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Call, contentDescription = "المكالمة الصوتية", tint = Violet)
            }
            Button(
                enabled = enabled && value.isNotBlank(),
                onClick = onSend,
                modifier = Modifier.size(42.dp),
                contentPadding = PaddingValues(0.dp),
                shape = CircleShape,
                colors = ButtonDefaults.buttonColors(containerColor = Violet)
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "إرسال", tint = Color.White)
            }
        }
    }
}
