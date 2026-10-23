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
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.Hub
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material.icons.filled.Code
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
private val Ink = Color(0xFF17245F)
private val Violet = Color(0xFF6725F5)
private val Blue = Color(0xFF287DFF)
private val Cyan = Color(0xFF5DE8FF)
private val Muted = Color(0xFF7584AE)
private val Line = Color(0xFFE0E8F7)
private val Glow = Brush.horizontalGradient(
    listOf(Cyan, Color(0xFF9F9CFF), Color(0xFFFFB8EC), Cyan)
)
private val LogoGradient = Brush.linearGradient(
    listOf(Color(0xFF1A41FF), Color(0xFF9B35FF), Color(0xFF42E9FF))
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

private data class UiTool(
    val title: String,
    val subtitle: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val prompt: String,
    val needsProvider: Boolean = false
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
    var selectedPage by remember { mutableStateOf("المكتبة") }
    var panel by remember { mutableStateOf("tools") }
    var showNavigation by remember { mutableStateOf(false) }
    var showTools by remember { mutableStateOf(false) }
    var dialogTitle by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    val tools = listOf(
        UiTool("إنشاء صور", "إنشاء صور", Icons.Default.Image,
            "ساعدني في إعداد وصف تفصيلي لصورة عن: ", true),
        UiTool("فيديو (مع Veo)", "تخطيط · إنشاء فيديو", Icons.Default.VideoLibrary,
            "ساعدني في كتابة فكرة وسيناريو فيديو عن: ", true),
        UiTool("توليد الموسيقى", "موسيقى وصوت", Icons.Default.MusicNote,
            "اكتب لي فكرة موسيقية وكلمات عن: ", true),
        UiTool("Canyova", "التصميم والإبداع", Icons.Default.Code,
            "ساعدني في إنشاء تصميم عن: "),
        UiTool("Deep Research", "بحث وتحليل", Icons.Default.Search,
            "ابحث وحلّل الموضوع التالي بالتفصيل: "),
        UiTool("التعلم الموجّه", "شرح وتدريب", Icons.Default.School,
            "علّمني خطوة بخطوة: "),
        UiTool("الذكاء الموسيقي", "مساعد ذكي", Icons.Default.AutoAwesome,
            "ساعدني في إنجاز المهمة التالية: "),
        UiTool("المزيد", "كل الأدوات", Icons.Default.Hub,
            "ساعدني في اختيار الأداة المناسبة لمهمتي: ")
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
        BoxWithConstraints(
            Modifier.fillMaxSize().background(
                Brush.verticalGradient(
                    listOf(Color(0xFFF8FBFF), Color(0xFFF0F5FF), Color.White)
                )
            )
        ) {
            val wide = maxWidth >= 900.dp
            val medium = maxWidth >= 620.dp

            Row(Modifier.fillMaxSize()) {
                if (wide || showNavigation) {
                    NavigationPanel(
                        selected = selectedPage,
                        onSelect = {
                            selectedPage = it
                            showNavigation = false
                            when (it) {
                                "دردشة جديدة" -> {
                                    messages.clear()
                                    messages.add(
                                        ChatMessage(
                                            "assistant",
                                            "مرحبًا بك في Lazaynova 👋\nأنا مساعدك الذكي، جاهز لمساعدتك في أي شيء تحتاجه."
                                        )
                                    )
                                    input = ""
                                    error = null
                                }
                                "المكتبة", "الرئيسية" -> Unit
                                else -> dialogTitle = it
                            }
                        },
                        modifier = Modifier.width(if (wide) 235.dp else maxWidth * .82f)
                    )
                }

                Column(
                    Modifier.weight(1f).fillMaxHeight()
                ) {
                    Header(
                        onMenu = { showNavigation = !showNavigation },
                        onTools = { showTools = !showTools },
                        onAccount = { dialogTitle = "حساب Lazaynova" }
                    )

                    if (!wide && showTools) {
                        ToolsPanel(
                            tools = tools,
                            compact = true,
                            onTool = {
                                showTools = false
                                if (it.needsProvider) dialogTitle = it.title
                                else input = it.prompt
                            },
                            modifier = Modifier.fillMaxWidth().heightIn(max = 290.dp)
                        )
                    }

                    Row(Modifier.weight(1f).fillMaxWidth()) {
                        Column(Modifier.weight(1f).fillMaxHeight()) {
                            LazyColumn(
                                Modifier.weight(1f).fillMaxWidth(),
                                contentPadding = PaddingValues(
                                    horizontal = if (medium) 18.dp else 12.dp,
                                    vertical = 12.dp
                                ),
                                verticalArrangement = Arrangement.spacedBy(14.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                item {
                                    HeroSection(compact = !medium)
                                }

                                if (!wide) {
                                    item {
                                        Row(
                                            Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                                        ) {
                                            OutlinedButton(
                                                onClick = { showNavigation = !showNavigation },
                                                modifier = Modifier.weight(1f),
                                                shape = RoundedCornerShape(14.dp)
                                            ) {
                                                Text("التنقل")
                                            }
                                            OutlinedButton(
                                                onClick = { showTools = !showTools },
                                                modifier = Modifier.weight(1f),
                                                shape = RoundedCornerShape(14.dp)
                                            ) {
                                                Text("المكونات الإضافية")
                                            }
                                        }
                                    }
                                }

                                item {
                                    TaskPicker(
                                        tools = tools,
                                        compact = !medium,
                                        onTool = {
                                            if (it.needsProvider) {
                                                dialogTitle = it.title
                                            } else {
                                                input = it.prompt
                                            }
                                        }
                                    )
                                }

                                item {
                                    Row(
                                        Modifier.fillMaxWidth(),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            "المحادثة",
                                            color = Ink,
                                            fontSize = 18.sp,
                                            fontWeight = FontWeight.Bold
                                        )
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
                                            containerColor = if (assistant) Color.White
                                            else Color(0xFFF0ECFF)
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
                                            Text(
                                                message.text,
                                                color = Ink,
                                                fontSize = 14.sp,
                                                lineHeight = 23.sp
                                            )
                                        }
                                    }
                                }

                                if (busy) {
                                    item {
                                        Row(
                                            Modifier.fillMaxWidth().padding(8.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            CircularProgressIndicator(
                                                Modifier.size(20.dp),
                                                strokeWidth = 2.dp
                                            )
                                            Spacer(Modifier.width(10.dp))
                                            Text("يجري إعداد الرد...", color = Muted)
                                        }
                                    }
                                }

                                error?.let { problem ->
                                    item {
                                        Text(problem, color = Color(0xFFB3261E), fontSize = 12.sp)
                                    }
                                }
                            }

                            ChatComposer(
                                value = input,
                                onValueChange = { input = it },
                                enabled = !busy,
                                onAdd = { dialogTitle = "إضافة ملف أو صورة" },
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

                        if (wide) {
                            ToolsPanel(
                                tools = tools,
                                compact = true,
                                onTool = {
                                    if (it.needsProvider) dialogTitle = it.title
                                    else input = it.prompt
                                },
                                modifier = Modifier.width(235.dp).fillMaxHeight()
                                    .padding(end = 10.dp, bottom = 10.dp)
                            )
                        }
                    }
                }
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
                                "فيديو (مع Veo)" ->
                                    "تخطيط الفيديو وكتابة السيناريو متاحان عبر المحادثة. إنشاء ملف فيديو يحتاج إلى خدمة توليد فيديو."
                                "توليد الموسيقى" ->
                                    "يمكنك طلب كلمات الأغاني والأفكار الموسيقية من المساعد. توليد الصوت يحتاج إلى مزوّد صوت."
                                "إضافة ملف أو صورة" ->
                                    "اختيار الملفات يحتاج إلى إضافة منتقي ملفات ومعالجة المحتوى. هذه الوظيفة لم تُربط بعد."
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
private fun Header(
    onMenu: () -> Unit,
    onTools: () -> Unit,
    onAccount: () -> Unit
) {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Surface(
            onClick = onMenu,
            shape = RoundedCornerShape(13.dp),
            color = Color.White,
            border = androidx.compose.foundation.BorderStroke(1.dp, Line)
        ) {
            Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Menu, "القائمة", tint = Ink)
            }
        }
        Spacer(Modifier.weight(1f))
        Text("✦", color = Violet, fontSize = 27.sp)
        Spacer(Modifier.width(6.dp))
        Text(
            "Lazaynova",
            color = Color(0xFF2527A6),
            fontSize = 22.sp,
            fontWeight = FontWeight.ExtraBold
        )
        Spacer(Modifier.weight(1f))
        Surface(
            onClick = onTools,
            shape = RoundedCornerShape(13.dp),
            color = Color.White,
            border = androidx.compose.foundation.BorderStroke(1.dp, Line)
        ) {
            Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) {
                Text("⋯", color = Ink, fontSize = 25.sp)
            }
        }
    }
}

@Composable
private fun NavigationPanel(
    selected: String,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier.fillMaxHeight().background(Color(0xFFF8FAFF))
            .border(width = 1.dp, color = Line)
            .verticalScroll(rememberScrollState()).padding(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LogoMark(54.dp)
            Spacer(Modifier.width(8.dp))
            Text(
                "Lazaynova",
                color = Color(0xFF2527A6),
                fontSize = 19.sp,
                fontWeight = FontWeight.ExtraBold
            )
        }
        Spacer(Modifier.height(15.dp))
        OutlinedTextField(
            value = "",
            onValueChange = {},
            enabled = false,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("بحث", fontSize = 12.sp) },
            leadingIcon = { Icon(Icons.Default.Search, null) },
            shape = RoundedCornerShape(18.dp),
            singleLine = true
        )
        Spacer(Modifier.height(10.dp))
        val primary = listOf(
            "دردشة جديدة" to Icons.Default.AutoAwesome,
            "المحادثات" to Icons.Default.History,
            "المكتبة" to Icons.Default.Folder,
            "الوسائط" to Icons.Default.Image,
            "المستندات" to Icons.Default.Description,
            "جدولة" to Icons.Default.CalendarMonth
        )
        primary.forEach { (name, icon) ->
            NavigationItem(name, icon, selected == name) { onSelect(name) }
        }
        HorizontalDivider(Modifier.padding(vertical = 10.dp), color = Line)
        Text("الإعدادات الأساسية", color = Muted, fontSize = 12.sp)
        listOf(
            "المظهر" to Icons.Default.Settings,
            "اللغة" to Icons.Default.Language,
            "صوت الوكيل" to Icons.Default.GraphicEq,
            "الإشعارات" to Icons.Default.Notifications
        ).forEach { (name, icon) -> NavigationItem(name, icon, selected == name) { onSelect(name) } }
        HorizontalDivider(Modifier.padding(vertical = 10.dp), color = Line)
        Text("المميزات المتقدمة", color = Muted, fontSize = 12.sp)
        listOf(
            "الوكلاء" to Icons.Default.Hub,
            "الذاكرة" to Icons.Default.Memory,
            "التكاملات" to Icons.Default.Link,
            "الأمان والخصوصية" to Icons.Default.Security,
            "السجلات والتحليلات" to Icons.Default.BarChart
        ).forEach { (name, icon) -> NavigationItem(name, icon, selected == name) { onSelect(name) } }
        Spacer(Modifier.height(15.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = Color.White),
            border = androidx.compose.foundation.BorderStroke(1.dp, Line),
            shape = RoundedCornerShape(17.dp)
        ) {
            Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                LogoMark(38.dp)
                Spacer(Modifier.width(8.dp))
                Column {
                    Text("Lazaynova Core", color = Ink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text("الموكيل الرئيسي", color = Muted, fontSize = 10.sp)
                }
            }
        }
        NavigationItem("الحساب والاشتراكات", Icons.Default.AccountCircle, selected == "الحساب والاشتراكات") {
            onSelect("الحساب والاشتراكات")
        }
        Spacer(Modifier.height(12.dp))
        Text("الإصدار 0.1", Modifier.fillMaxWidth(), color = Muted, textAlign = TextAlign.Center, fontSize = 10.sp)
    }
}

@Composable
private fun NavigationItem(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    selected: Boolean,
    onClick: () -> Unit
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 2.dp)
            .background(
                if (selected) Color(0xFFEAEAFF) else Color.Transparent,
                RoundedCornerShape(12.dp)
            ).clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = title, tint = if (selected) Violet else Ink, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(12.dp))
        Text(title, color = Ink, fontSize = 12.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium)
    }
}

@Composable
private fun HeroSection(compact: Boolean) {
    Column(
        Modifier.fillMaxWidth().padding(top = if (compact) 5.dp else 14.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        LogoMark(if (compact) 142.dp else 190.dp)
        Spacer(Modifier.height(5.dp))
        Text(
            "Lazaynova",
            fontSize = if (compact) 31.sp else 40.sp,
            fontWeight = FontWeight.Black,
            style = TextStyle(
                brush = Brush.horizontalGradient(
                    listOf(Color(0xFF168DFF), Violet, Color(0xFFCA4DFF))
                )
            )
        )
        Spacer(Modifier.height(20.dp))
        Text(
            "مرحبًا بك في Lazaynova 👋",
            fontSize = if (compact) 20.sp else 23.sp,
            fontWeight = FontWeight.Bold,
            color = Ink,
            textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(9.dp))
        Text(
            "أنا مساعدك الذكي، جاهز لمساعدتك في أي شيء\nتخيله أو تحتاجه.",
            fontSize = if (compact) 14.sp else 16.sp,
            color = Color(0xFF4D5883),
            textAlign = TextAlign.Center,
            lineHeight = 25.sp
        )
        Spacer(Modifier.height(12.dp))
    }
}

@Composable
private fun LogoMark(size: androidx.compose.ui.unit.Dp) {
    Box(
        Modifier.size(size).shadow(15.dp, RoundedCornerShape(size * .25f), ambientColor = Violet.copy(alpha = .2f))
            .background(Glow, RoundedCornerShape(size * .25f))
            .padding(2.dp)
            .background(Color.White, RoundedCornerShape(size * .25f)),
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
private fun TaskPicker(
    tools: List<UiTool>,
    compact: Boolean,
    onTool: (UiTool) -> Unit
) {
    Card(
        Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(25.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = .92f)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Line),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(Modifier.padding(if (compact) 10.dp else 15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("×", color = Muted, fontSize = 22.sp)
                Spacer(Modifier.weight(1f))
                Text("اختيار المهام", color = Ink, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Spacer(Modifier.weight(1f))
                Text("✦", color = Violet, fontSize = 19.sp)
            }
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                MiniTask("صورة", Icons.Default.Image, Modifier.weight(1f)) { onTool(tools[0]) }
                MiniTask("كاميرا", Icons.Default.Image, Modifier.weight(1f)) { onTool(tools[0]) }
                MiniTask("ملفات", Icons.Default.Description, Modifier.weight(1f)) { onTool(tools[7]) }
            }
            Spacer(Modifier.height(12.dp))
            val rows = tools.chunked(if (compact) 2 else 4)
            rows.forEach { row ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(7.dp)
                ) {
                    row.forEach { tool ->
                        Card(
                            onClick = { onTool(tool) },
                            modifier = Modifier.weight(1f).height(if (compact) 98.dp else 112.dp),
                            shape = RoundedCornerShape(17.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (tool.title == "الذكاء الموسيقي")
                                    Color(0xFFF6F0FF) else Color(0xFFF9FBFF)
                            ),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Line)
                        ) {
                            Column(
                                Modifier.fillMaxSize().padding(5.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                Icon(tool.icon, contentDescription = tool.title, tint = Violet, modifier = Modifier.size(28.dp))
                                Spacer(Modifier.height(7.dp))
                                Text(
                                    tool.title,
                                    color = Ink,
                                    fontSize = if (compact) 10.sp else 11.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    textAlign = TextAlign.Center
                                )
                            }
                        }
                    }
                    repeat((if (compact) 2 else 4) - row.size) {
                        Spacer(Modifier.weight(1f))
                    }
                }
                Spacer(Modifier.height(7.dp))
            }
            Spacer(Modifier.height(5.dp))
            Text(
                "يمكنك الوصول إلى جميع الأدوات والميزات من هنا.\nاختر ما تحتاجه لبدء مهمتك مع Lazaynova.",
                Modifier.fillMaxWidth().background(Color(0xFFF1F6FF), RoundedCornerShape(15.dp))
                    .padding(12.dp),
                color = Muted,
                fontSize = 11.sp,
                lineHeight = 19.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun MiniTask(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = modifier.height(48.dp),
        shape = RoundedCornerShape(13.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF4F8FF)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Line)
    ) {
        Row(
            Modifier.fillMaxSize().padding(horizontal = 5.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = title, tint = Violet, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(5.dp))
            Text(title, color = Ink, fontSize = 11.sp)
        }
    }
}

@Composable
private fun ToolsPanel(
    tools: List<UiTool>,
    compact: Boolean,
    onTool: (UiTool) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier.background(Color(0xFFF8FAFF)).border(1.dp, Line)
            .verticalScroll(rememberScrollState()).padding(9.dp)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = Color.White),
            shape = RoundedCornerShape(17.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Line)
        ) {
            Row(
                Modifier.fillMaxWidth().clickable { }.padding(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    Modifier.size(42.dp).background(Glow, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.AccountCircle, null, tint = Color.White, modifier = Modifier.size(27.dp))
                }
                Spacer(Modifier.width(8.dp))
                Column(Modifier.weight(1f)) {
                    Text("زايد الجبجي", color = Ink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text("حساب مجاني", color = Muted, fontSize = 10.sp)
                }
                Text("›", color = Muted, fontSize = 22.sp)
            }
        }
        Spacer(Modifier.height(10.dp))
        Text("المكونات الإضافية", color = Ink, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(7.dp))
        ToolRow(
            "الوكيل الذكي", "تفكير · تخطيط · تنفيذ", Icons.Default.SmartToy,
            onClick = { onTool(UiTool("الوكيل الذكي", "", Icons.Default.SmartToy, "ساعدني في تنفيذ هذه المهمة: ")) }
        )
        ToolRow("رفع الصور", "تحليل · استفسار", Icons.Default.Image,
            onClick = { onTool(tools[0]) })
        ToolRow("رفع الملفات", "ملفات · مستندات", Icons.Default.Folder,
            onClick = { onTool(tools[7]) })
        Spacer(Modifier.height(12.dp))
        Text("المميزات والمهام الرئيسية", color = Ink, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(7.dp))
        tools.forEach { tool ->
            ToolRow(tool.title, tool.subtitle, tool.icon) { onTool(tool) }
        }
        Spacer(Modifier.height(10.dp))
        Card(
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFF0EFFF)),
            border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE3DAFF))
        ) {
            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.MusicNote, null, tint = Violet, modifier = Modifier.size(35.dp))
                Spacer(Modifier.width(9.dp))
                Column {
                    Text("توليد الموسيقى", color = Violet, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Text("أفكارك، بصوت. يتطلب مزوّدًا متصلًا.", color = Muted, fontSize = 10.sp)
                }
            }
        }
    }
}

@Composable
private fun ToolRow(
    title: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
        shape = RoundedCornerShape(15.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = androidx.compose.foundation.BorderStroke(1.dp, Line)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                Modifier.size(39.dp).background(Color(0xFFF0EDFF), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = title, tint = Violet, modifier = Modifier.size(22.dp))
            }
            Spacer(Modifier.width(8.dp))
            Column(Modifier.weight(1f)) {
                Text(title, color = Ink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                if (subtitle.isNotBlank()) {
                    Text(subtitle, color = Muted, fontSize = 10.sp)
                }
            }
            Text("›", color = Muted, fontSize = 21.sp)
        }
    }
}

@Composable
private fun ChatComposer(
    value: String,
    onValueChange: (String) -> Unit,
    enabled: Boolean,
    onAdd: () -> Unit,
    onSend: () -> Unit
) {
    Card(
        Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 5.dp)
            .shadow(10.dp, RoundedCornerShape(30.dp), ambientColor = Violet.copy(alpha = .16f))
            .border(2.dp, Glow, RoundedCornerShape(30.dp)),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(
            Modifier.padding(7.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                onClick = onAdd,
                shape = CircleShape,
                color = Color(0xFFF1EDFF)
            ) {
                Box(Modifier.size(43.dp), contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Add, "إضافة", tint = Violet)
                }
            }
            Spacer(Modifier.width(8.dp))
            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.weight(1f).padding(vertical = 12.dp),
                textStyle = TextStyle(color = Ink, fontSize = 14.sp),
                decorationBox = { inner ->
                    Box {
                        if (value.isEmpty()) {
                            Text("اسأل Lazaynova...", color = Muted, fontSize = 14.sp)
                        }
                        inner()
                    }
                }
            )
            Spacer(Modifier.width(7.dp))
            Button(
                enabled = enabled && value.isNotBlank(),
                onClick = onSend,
                modifier = Modifier.size(46.dp),
                contentPadding = PaddingValues(0.dp),
                shape = CircleShape,
                colors = ButtonDefaults.buttonColors(containerColor = Violet)
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "إرسال", tint = Color.White)
            }
        }
    }
}
