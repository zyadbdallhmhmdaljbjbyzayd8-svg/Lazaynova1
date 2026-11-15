package com.lazaynova.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.ViewModelProvider
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import kotlinx.coroutines.launch

private val Page = Color(0xFFF7F9FC)
private val White = Color(0xFFFFFFFF)
private val Primary = Color(0xFF6D5CE8)
private val PrimaryDark = Color(0xFF7C3AED)
private val Ink = Color(0xFF1E293B)
private val Muted = Color(0xFF64748B)
private val Line = Color(0xFFE8EAF2)
private val SoftPurple = Color(0xFFF0EDFF)
private val LogoBrush = Brush.linearGradient(
    listOf(Color(0xFF8B5CF6), Color(0xFF6366F1), Color(0xFF38BDF8))
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val chatViewModel = ViewModelProvider(this)[ChatViewModel::class.java]

        window.statusBarColor = android.graphics.Color.rgb(247, 249, 252)
        window.navigationBarColor = android.graphics.Color.rgb(247, 249, 252)
        window.decorView.systemUiVisibility =
            android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
            android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR

        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = Primary,
                    onPrimary = White,
                    background = Page,
                    surface = White,
                    onSurface = Ink
                )
            ) {
                CompositionLocalProvider(
                    LocalLayoutDirection provides LayoutDirection.Rtl
                ) {
                    LazaynovaRoot(chatViewModel)
                }
            }
        }
    }
}

private data class ToolEntry(
    val title: String,
    val subtitle: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val prompt: String,
    val engine: String = "chat"
)

private val toolEntries = listOf(
    ToolEntry("إضافة ملف", "اختر ملفاً من جهازك", Icons.Default.AttachFile, ""),
    ToolEntry("إضافة صورة", "اختيار صورة", Icons.Default.Image, ""),
    ToolEntry("إنشاء PDF", "إعداد مستند PDF", Icons.Default.PictureAsPdf, "ساعدني في إعداد مستند PDF: "),
    ToolEntry("بحث عميق", "بحث وتحليل متقدم", Icons.Default.TravelExplore, "ابدأ بحثاً عميقاً حول: ", "research"),
    ToolEntry("تلخيص", "تلخيص النصوص والمستندات", Icons.Default.Summarize, "لخّص ما يلي: "),
    ToolEntry("بدء التنفيذ", "تنسيق مهمة متعددة الخطوات", Icons.Default.PlayArrow, "خطط ونفّذ المهمة التالية خطوة بخطوة: ", "agent"),
    ToolEntry("تخطيط المهام", "تحويل الهدف إلى خطة", Icons.Default.Checklist, "أنشئ خطة تنفيذ للمهمة التالية: ", "agent"),
    ToolEntry("إدارة المهام", "تنظيم سير العمل", Icons.Default.TaskAlt, "ساعدني في تنظيم هذه المهام: ", "agent"),
    ToolEntry("إنشاء الصور", "إعداد وصف لصورة", Icons.Default.Palette, "أنشئ وصفاً تفصيلياً للصورة التالية: ", "image"),
    ToolEntry("إنشاء الفيديو", "إعداد فكرة فيديو", Icons.Default.Movie, "ساعدني في إعداد سيناريو فيديو حول: ", "video"),
    ToolEntry("إنشاء الموسيقى", "تأليف فكرة موسيقية", Icons.Default.MusicNote, "ساعدني في إعداد فكرة موسيقية حول: ", "music"),
    ToolEntry("التعليم", "شرح وتعلّم خطوة بخطوة", Icons.Default.School, "علّمني الموضوع التالي تدريجياً: ")
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LazaynovaRoot(viewModel: ChatViewModel) {
    val state by viewModel.uiState.collectAsState()
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    var showTools by remember { mutableStateOf(false) }
    var showMore by remember { mutableStateOf(false) }
    var dialogTitle by remember { mutableStateOf<String?>(null) }
    var dialogText by remember { mutableStateOf("") }

    val filePicker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            dialogTitle = "تم اختيار الملف"
            dialogText = "تم اختيار الملف من الجهاز، لكن محتواه لم يُرفع إلى الخادم بعد."
        }
    }

    val imagePicker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            dialogTitle = "تم اختيار الصورة"
            dialogText = "تم تحديد الصورة على الجهاز. لم يتم إرسال محتواها إلى محرك الصور بعد."
        }
    }

    BackHandler(
        enabled = drawerState.isOpen || showTools || dialogTitle != null || showMore
    ) {
        when {
            dialogTitle != null -> dialogTitle = null
            showTools -> showTools = false
            showMore -> showMore = false
            drawerState.isOpen -> scope.launch { drawerState.close() }
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = true,
        drawerContent = {
            ModalDrawerSheet(
                modifier = Modifier.fillMaxWidth(0.86f).fillMaxHeight(),
                drawerContainerColor = White,
                drawerShape = RoundedCornerShape(topStart = 0.dp, bottomStart = 0.dp)
            ) {
                LazaynovaDrawer(
                    onClose = { scope.launch { drawerState.close() } },
                    onNewChat = {
                        viewModel.newConversation()
                        scope.launch { drawerState.close() }
                    },
                    onItem = { title ->
                        scope.launch { drawerState.close() }
                        dialogTitle = title
                        dialogText = drawerDescription(title)
                    },
                    onTool = { title, engine ->
                        viewModel.selectEngine(engine)
                        viewModel.updateInput("$title: ")
                        scope.launch { drawerState.close() }
                    }
                )
            }
        }
    ) {
        Scaffold(
            containerColor = Page,
            topBar = {
                Column {
                    LazaynovaTopBar(
                        selectedEngine = state.selectedEngine,
                        onMenu = { scope.launch { drawerState.open() } },
                        onMore = { showMore = true },
                        onEngine = viewModel::selectEngine
                    )
                    ModelQuickPills(
                        selectedEngine = state.selectedEngine,
                        onSelect = viewModel::selectEngine
                    )
                }
            },
            bottomBar = {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .background(Page)
                        .navigationBarsPadding()
                ) {
                    ChatInputBar(
                        value = state.input,
                        enabled = !state.isBusy,
                        onValueChange = viewModel::updateInput,
                        onAdd = { showTools = true },
                        onMic = {
                            dialogTitle = "الإدخال الصوتي"
                            dialogText = "واجهة الميكروفون جاهزة. تسجيل الصوت وتحويله إلى نص يحتاج إلى خدمة صوتية فعلية."
                        },
                        onCall = {
                            dialogTitle = "المحادثة الصوتية"
                            dialogText = "المحادثة الصوتية المباشرة تحتاج إلى ربط خدمة الصوت."
                        },
                        onSend = viewModel::sendMessage
                    )
                    Text(
                        "LAZAYNOVA AI  ·  Private. Autonomous. Yours.",
                        Modifier.fillMaxWidth().padding(bottom = 7.dp),
                        color = Muted.copy(alpha = 0.8f),
                        fontSize = 9.sp,
                        textAlign = TextAlign.Center
                    )
                }
            }
        ) { padding ->
            Column(
                Modifier
                    .fillMaxSize()
                    .background(Page)
                    .padding(padding)
            ) {
                if (state.messages.size <= 1) {
                    HeroContent()
                } else {
                    ChatMessages(
                        messages = state.messages,
                        isBusy = state.isBusy,
                        error = state.error,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }


    var authUsername by remember { mutableStateOf("") }
    var authPassword by remember { mutableStateOf("") }
    var createAccount by remember { mutableStateOf(false) }

    if (!state.isAuthenticated) {
        AlertDialog(
            onDismissRequest = { },
            title = { Text("الاتصال بمركزية LAZAYNOVA") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        if (createAccount) "إنشاء حساب جديد على الخادم المحلي"
                        else "سجّل الدخول للاتصال بالخادم المركزي"
                    )
                    OutlinedTextField(
                        value = authUsername,
                        onValueChange = { authUsername = it },
                        label = { Text("اسم المستخدم") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = authPassword,
                        onValueChange = { authPassword = it },
                        label = { Text("كلمة المرور") },
                        singleLine = true
                    )
                    state.authError?.let { authError ->
                        Text(authError, color = MaterialTheme.colorScheme.error)
                    }
                }
            },
            confirmButton = {
                Button(
                    enabled = !state.isAuthenticating,
                    onClick = {
                        viewModel.authenticate(
                            authUsername,
                            authPassword,
                            createAccount
                        )
                    }
                ) {
                    Text(
                        if (state.isAuthenticating) "جارٍ الاتصال..."
                        else if (createAccount) "إنشاء الحساب" else "تسجيل الدخول"
                    )
                }
            },
            dismissButton = {
                TextButton(
                    enabled = !state.isAuthenticating,
                    onClick = { createAccount = !createAccount }
                ) {
                    Text(if (createAccount) "لدي حساب بالفعل" else "إنشاء حساب جديد")
                }
            }
        )
    }

    if (showTools) {
        ModalBottomSheet(
            onDismissRequest = { showTools = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = White,
            shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
            dragHandle = {
                Box(
                    Modifier
                        .padding(top = 10.dp, bottom = 8.dp)
                        .size(width = 42.dp, height = 4.dp)
                        .clip(CircleShape)
                        .background(Line)
                )
            }
        ) {
            ToolsBottomSheet(
                onTool = { tool ->
                    showTools = false
                    when (tool.title) {
                        "إضافة ملف" -> filePicker.launch(arrayOf("*/*"))
                        "إضافة صورة" -> imagePicker.launch("image/*")
                        else -> {
                            viewModel.selectEngine(tool.engine)
                            viewModel.updateInput(tool.prompt)
                        }
                    }
                }
            )
        }
    }

    if (showMore) {
        AlertDialog(
            onDismissRequest = { showMore = false },
            containerColor = White,
            title = { Text("خيارات LAZAYNOVA", color = Ink, fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    TextButton(onClick = {
                        showMore = false
                        viewModel.newConversation()
                    }) {
                        Icon(Icons.Default.Add, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("محادثة جديدة")
                    }
                    TextButton(onClick = {
                        showMore = false
                        dialogTitle = "حول LAZAYNOVA AI"
                        dialogText = "LAZAYNOVA AI\nPrivate. Autonomous. Yours.\nواجهة التطبيق الرئيسية."
                    }) {
                        Icon(Icons.Default.Info, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("حول التطبيق")
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showMore = false }) { Text("إغلاق") }
            }
        )
    }

    if (dialogTitle != null) {
        AlertDialog(
            onDismissRequest = { dialogTitle = null },
            containerColor = White,
            title = { Text(dialogTitle.orEmpty(), color = Ink, fontWeight = FontWeight.Bold) },
            text = { Text(dialogText, color = Muted, lineHeight = 23.sp) },
            confirmButton = {
                TextButton(onClick = { dialogTitle = null }) {
                    Text("حسناً", color = Primary)
                }
            }
        )
    }
}

@Composable
private fun LazaynovaTopBar(
    selectedEngine: String,
    onMenu: () -> Unit,
    onMore: () -> Unit,
    onEngine: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    val selected = LazaynovaEngines.firstOrNull { it.id == selectedEngine }
        ?: LazaynovaEngines.first()

    Row(
        Modifier
            .fillMaxWidth()
            .background(Page)
            .padding(horizontal = 14.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Surface(
            onClick = onMenu,
            shape = RoundedCornerShape(14.dp),
            color = White,
            border = BorderStroke(1.dp, Line),
            modifier = Modifier.size(42.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Menu, contentDescription = "القائمة", tint = Ink)
            }
        }

        Spacer(Modifier.weight(1f))

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                "Lazaynova",
                color = Ink,
                fontSize = 19.sp,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = (-0.5).sp
            )
            Box {
                Surface(
                    onClick = { expanded = true },
                    shape = RoundedCornerShape(20.dp),
                    color = SoftPurple
                ) {
                    Row(
                        Modifier.padding(horizontal = 11.dp, vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Memory,
                            contentDescription = null,
                            tint = Primary,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(Modifier.width(5.dp))
                        Text(selected.title, color = PrimaryDark, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.width(4.dp))
                        Icon(Icons.Default.ExpandMore, contentDescription = null, tint = Primary)
                    }
                }
                DropdownMenu(
                    expanded = expanded,
                    onDismissRequest = { expanded = false }
                ) {
                    LazaynovaEngines.forEach { engine ->
                        DropdownMenuItem(
                            text = { Text(engine.title) },
                            onClick = {
                                onEngine(engine.id)
                                expanded = false
                            },
                            leadingIcon = {
                                Icon(Icons.Default.Memory, contentDescription = null)
                            }
                        )
                    }
                }
            }
        }

        Spacer(Modifier.weight(1f))

        Box {
            Surface(
                onClick = onMore,
                shape = RoundedCornerShape(14.dp),
                color = White,
                border = BorderStroke(1.dp, Line),
                modifier = Modifier.size(42.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.MoreVert, contentDescription = "المزيد", tint = Ink)
                }
            }
        }
    }
}

@Composable
private fun ModelQuickPills(
    selectedEngine: String,
    onSelect: (String) -> Unit
) {
    val quick = listOf(
        "chat" to "L4.5",
        "coding" to "L3",
        "research" to "L4",
        "agent" to "L5"
    )

    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(9.dp)
    ) {
        quick.forEach { (id, label) ->
            val active = selectedEngine == id
            Surface(
                onClick = { onSelect(id) },
                shape = RoundedCornerShape(22.dp),
                color = if (active) Primary else White,
                border = BorderStroke(1.dp, if (active) Primary else Line)
            ) {
                Row(
                    Modifier.padding(horizontal = 18.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (active) {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            tint = White,
                            modifier = Modifier.size(13.dp)
                        )
                        Spacer(Modifier.width(5.dp))
                    }
                    Text(
                        label,
                        color = if (active) White else Ink,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

@Composable
private fun HeroContent() {
    Column(
        Modifier
            .fillMaxSize()
            .background(
                Brush.radialGradient(
                    colors = listOf(
                        Color(0x1E8B5CF6),
                        Color(0x0C6366F1),
                        Page
                    ),
                    radius = 620f
                )
            )
            .padding(horizontal = 22.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            Modifier.size(190.dp),
            contentAlignment = Alignment.Center
        ) {
            Box(
                Modifier
                    .size(174.dp)
                    .border(
                        1.dp,
                        Brush.linearGradient(
                            listOf(
                                Color(0x558B5CF6),
                                Color(0x5538BDF8),
                                Color(0x55EC4899)
                            )
                        ),
                        CircleShape
                    )
            )
            Box(
                Modifier
                    .size(145.dp)
                    .border(1.dp, Color(0x338B5CF6), CircleShape)
            )
            Box(
                Modifier
                    .size(112.dp)
                    .shadow(22.dp, RoundedCornerShape(34.dp), ambientColor = Primary.copy(alpha = .18f))
                    .background(
                        Brush.linearGradient(
                            listOf(Color(0xFFEEE8FF), Color(0xFFE4F1FF), Color(0xFFFCE7F3))
                        ),
                        RoundedCornerShape(34.dp)
                    )
                    .border(1.dp, White, RoundedCornerShape(34.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    "L",
                    fontSize = 83.sp,
                    fontWeight = FontWeight.Black,
                    style = TextStyle(brush = LogoBrush)
                )
            }
            Box(
                Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = (-17).dp, y = 20.dp)
                    .size(10.dp)
                    .background(Color(0xFF38BDF8), CircleShape)
            )
            Box(
                Modifier
                    .align(Alignment.BottomStart)
                    .offset(x = 20.dp, y = (-18).dp)
                    .size(8.dp)
                    .background(Color(0xFFEC4899), CircleShape)
            )
        }

        Spacer(Modifier.height(8.dp))

        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            HorizontalDivider(Modifier.weight(1f), color = Color(0xFFDCD5F8))
            Column(
                Modifier.padding(horizontal = 15.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "LAZAYNOVA",
                    color = PrimaryDark,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 2.sp
                )
                Text(
                    "الزنوفا",
                    color = Muted,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium
                )
            }
            HorizontalDivider(Modifier.weight(1f), color = Color(0xFFDCD5F8))
        }

        Spacer(Modifier.height(38.dp))

        Text(
            "كيف أستطيع مساعدتك؟",
            color = Ink,
            fontSize = 25.sp,
            fontWeight = FontWeight.ExtraBold,
            textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(10.dp))
        Text(
            "اسأل، خطط، أنشئ، أو ابدأ بمشروع جديد.",
            color = Muted,
            fontSize = 14.sp,
            textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(24.dp))
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            HeroTag("اسأل", Icons.Default.Chat)
            HeroTag("خطط", Icons.Default.AutoAwesome)
            HeroTag("أنشئ", Icons.Default.Create)
        }
    }
}

@Composable
private fun HeroTag(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector
) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = White,
        border = BorderStroke(1.dp, Line)
    ) {
        Row(
            Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = null, tint = Primary, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(5.dp))
            Text(title, color = Muted, fontSize = 11.sp)
        }
    }
}

@Composable
private fun ChatMessages(
    messages: List<ChatMessage>,
    isBusy: Boolean,
    error: String?,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(13.dp)
    ) {
        items(messages.drop(1), key = { it.id }) { message ->
            val isUser = message.role == "user"
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = if (isUser) Arrangement.Start else Arrangement.End
            ) {
                Surface(
                    modifier = Modifier.widthIn(max = 310.dp),
                    shape = RoundedCornerShape(
                        topStart = 20.dp,
                        topEnd = 20.dp,
                        bottomStart = if (isUser) 5.dp else 20.dp,
                        bottomEnd = if (isUser) 20.dp else 5.dp
                    ),
                    color = if (isUser) SoftPurple else White,
                    border = BorderStroke(1.dp, if (isUser) Color(0xFFE4DDFE) else Line)
                ) {
                    Text(
                        message.text,
                        Modifier.padding(horizontal = 15.dp, vertical = 12.dp),
                        color = Ink,
                        fontSize = 14.sp,
                        lineHeight = 22.sp
                    )
                }
            }
        }

        if (isBusy) {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator(
                        Modifier.size(17.dp),
                        color = Primary,
                        strokeWidth = 2.dp
                    )
                    Spacer(Modifier.width(9.dp))
                    Text("تتم معالجة طلبك...", color = Muted, fontSize = 12.sp)
                }
            }
        }

        if (error != null) {
            item {
                Text(
                    error,
                    Modifier.fillMaxWidth(),
                    color = Color(0xFFB42318),
                    fontSize = 12.sp,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    value: String,
    enabled: Boolean,
    onValueChange: (String) -> Unit,
    onAdd: () -> Unit,
    onMic: () -> Unit,
    onCall: () -> Unit,
    onSend: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 13.dp, vertical = 8.dp)
            .shadow(10.dp, RoundedCornerShape(30.dp)),
        shape = RoundedCornerShape(30.dp),
        color = White,
        border = BorderStroke(1.dp, Color(0xFFE7E8F1))
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 7.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                onClick = onAdd,
                shape = CircleShape,
                color = SoftPurple,
                modifier = Modifier.size(39.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Add, contentDescription = "الأدوات", tint = Primary)
                }
            }

            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                enabled = enabled,
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 11.dp, vertical = 12.dp),
                textStyle = TextStyle(
                    color = Ink,
                    fontSize = 14.sp
                ),
                keyboardOptions = KeyboardOptions.Default,
                keyboardActions = KeyboardActions(
                    onSend = { if (enabled && value.isNotBlank()) onSend() }
                ),
                decorationBox = { inner ->
                    Box {
                        if (value.isEmpty()) {
                            Text("اكتب رسالتك هنا...", color = Color(0xFF9AA3B2), fontSize = 14.sp)
                        }
                        inner()
                    }
                }
            )

            IconButton(
                onClick = onMic,
                enabled = enabled,
                modifier = Modifier.size(34.dp)
            ) {
                Icon(Icons.Default.Mic, contentDescription = "الميكروفون", tint = Muted)
            }

            IconButton(
                onClick = onCall,
                enabled = enabled,
                modifier = Modifier.size(34.dp)
            ) {
                Icon(Icons.Default.Call, contentDescription = "المحادثة الصوتية", tint = Muted)
            }

            Spacer(Modifier.width(3.dp))

            Button(
                onClick = onSend,
                enabled = enabled && value.isNotBlank(),
                modifier = Modifier.size(43.dp),
                shape = CircleShape,
                contentPadding = PaddingValues(0.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Primary,
                    disabledContainerColor = Color(0xFFD9D5EA)
                )
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.Send,
                    contentDescription = "إرسال",
                    tint = White,
                    modifier = Modifier.size(19.dp)
                )
            }
        }
    }
}

@Composable
private fun LazaynovaDrawer(
    onClose: () -> Unit,
    onNewChat: () -> Unit,
    onItem: (String) -> Unit,
    onTool: (String, String) -> Unit
) {
    Column(
        Modifier
            .fillMaxSize()
            .background(White)
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 15.dp)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(vertical = 17.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            LogoMini()
            Spacer(Modifier.width(10.dp))
            Column {
                Text("Lazaynova", color = PrimaryDark, fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
                Text("Private. Autonomous. Yours.", color = Muted, fontSize = 9.sp)
            }
            Spacer(Modifier.weight(1f))
            IconButton(onClick = onClose) {
                Icon(Icons.Default.Close, contentDescription = "إغلاق", tint = Muted)
            }
        }

        DrawerHeading("الرئيسية")
        DrawerEntry("دردشة جديدة", Icons.Default.Add, onNewChat)
        DrawerEntry("البحث في المحادثات", Icons.Default.Search) { onItem("البحث في المحادثات") }
        DrawerEntry("المحادثات الأخيرة", Icons.Default.History) { onItem("المحادثات الأخيرة") }
        DrawerEntry("المشاريع", Icons.Default.Folder) { onItem("المشاريع") }
        DrawerEntry("فريق الوكلاء", Icons.Default.Groups) { onItem("فريق الوكلاء") }

        HorizontalDivider(Modifier.padding(vertical = 12.dp), color = Line)
        DrawerHeading("الميزات")

        DrawerEntry("إنشاء الصور", Icons.Default.Image) { onTool("إنشاء الصور", "image") }
        DrawerEntry("إنشاء الفيديو", Icons.Default.Movie) { onTool("إنشاء الفيديو", "video") }
        DrawerEntry("إنشاء الموسيقى", Icons.Default.MusicNote) { onTool("إنشاء الموسيقى", "music") }
        DrawerEntry("البحث العميق", Icons.Default.TravelExplore) { onTool("البحث العميق", "research") }
        DrawerEntry("البرمجة", Icons.Default.Code) { onTool("البرمجة", "coding") }
        DrawerEntry("إنشاء تطبيقات Android", Icons.Default.Android) { onTool("إنشاء تطبيق Android", "coding") }
        DrawerEntry("إنشاء مواقع Web", Icons.Default.Language) { onTool("إنشاء موقع ويب", "coding") }

        HorizontalDivider(Modifier.padding(vertical = 12.dp), color = Line)
        DrawerHeading("الإعدادات")

        DrawerEntry("محركات لازايوفا", Icons.Default.Memory) { onItem("محركات لازايوفا") }
        DrawerEntry("الذاكرة والخصوصية", Icons.Default.Security) { onItem("الذاكرة والخصوصية") }
        DrawerEntry("المظهر", Icons.Default.Palette) { onItem("المظهر") }
        DrawerEntry("الصوت واللغة", Icons.Default.RecordVoiceOver) { onItem("الصوت واللغة") }
        DrawerEntry("الاتصال والخادم", Icons.Default.Cloud) { onItem("الاتصال والخادم") }
        DrawerEntry("حول التطبيق", Icons.Default.Info) { onItem("حول التطبيق") }

        Spacer(Modifier.height(18.dp))
        Surface(
            color = Page,
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Line)
        ) {
            Row(
                Modifier.fillMaxWidth().padding(13.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                LogoMini()
                Spacer(Modifier.width(9.dp))
                Column {
                    Text("LAZAYNOVA AI", color = Ink, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Text("الإصدار 0.1.0", color = Muted, fontSize = 10.sp)
                }
            }
        }
        Spacer(Modifier.height(18.dp))
    }
}

@Composable
private fun LogoMini() {
    Box(
        Modifier
            .size(40.dp)
            .background(LogoBrush, RoundedCornerShape(13.dp)),
        contentAlignment = Alignment.Center
    ) {
        Text("L", color = White, fontSize = 29.sp, fontWeight = FontWeight.Black)
    }
}

@Composable
private fun DrawerHeading(title: String) {
    Text(
        title,
        Modifier.padding(start = 8.dp, top = 8.dp, bottom = 6.dp),
        color = Muted,
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold
    )
}

@Composable
private fun DrawerEntry(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit
) {
    NavigationDrawerItem(
        label = { Text(title, fontSize = 13.sp, fontWeight = FontWeight.Medium) },
        selected = false,
        onClick = onClick,
        icon = {
            Icon(icon, contentDescription = null, tint = Primary, modifier = Modifier.size(20.dp))
        },
        shape = RoundedCornerShape(13.dp),
        colors = NavigationDrawerItemDefaults.colors(
            unselectedContainerColor = White,
            unselectedTextColor = Ink
        ),
        modifier = Modifier.padding(vertical = 1.dp)
    )
}

@Composable
private fun ToolsBottomSheet(onTool: (ToolEntry) -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 18.dp)
            .navigationBarsPadding()
            .padding(bottom = 22.dp)
    ) {
        Text("أدوات LAZAYNOVA", color = Ink, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
        Text("اختر ما تريد إنجازه", color = Muted, fontSize = 12.sp)
        Spacer(Modifier.height(17.dp))

        val groups = listOf(
            "المحادثة والملفات" to toolEntries.take(5),
            "إدارة المهام والعمل" to toolEntries.subList(5, 8),
            "إنشاء المحتوى والتعلم" to toolEntries.drop(8)
        )

        groups.forEach { (heading, entries) ->
            Text(
                heading,
                Modifier.padding(vertical = 8.dp),
                color = PrimaryDark,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp
            )
            entries.chunked(2).forEach { pair ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(9.dp)
                ) {
                    pair.forEach { tool ->
                        Card(
                            onClick = { onTool(tool) },
                            modifier = Modifier.weight(1f).padding(bottom = 8.dp),
                            shape = RoundedCornerShape(17.dp),
                            colors = CardDefaults.cardColors(containerColor = Page),
                            border = BorderStroke(1.dp, Line)
                        ) {
                            Column(
                                Modifier.fillMaxWidth().padding(horizontal = 9.dp, vertical = 13.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Icon(tool.icon, contentDescription = null, tint = Primary, modifier = Modifier.size(24.dp))
                                Spacer(Modifier.height(7.dp))
                                Text(
                                    tool.title,
                                    color = Ink,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    textAlign = TextAlign.Center
                                )
                                Text(
                                    tool.subtitle,
                                    color = Muted,
                                    fontSize = 9.sp,
                                    textAlign = TextAlign.Center,
                                    lineHeight = 13.sp
                                )
                            }
                        }
                    }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

private fun drawerDescription(title: String): String {
    return when (title) {
        "البحث في المحادثات" -> "واجهة البحث في سجل المحادثات. حفظ المحادثات والبحث الدائم يحتاجان إلى تخزين محلي لم يُربط بعد."
        "المحادثات الأخيرة" -> "ستظهر المحادثات المحفوظة هنا بعد إضافة نظام حفظ واستعادة المحادثات."
        "المشاريع" -> "مساحة المشاريع ستُربط بإدارة ملفات ومهام المشاريع."
        "فريق الوكلاء" -> "واجهة فريق الوكلاء. تنفيذ الوكلاء يعتمد على خدمات الخادم المتاحة."
        "محركات لازايوفا" -> "اختر المحرك من أزرار L4.5 وL3 وL4 وL5 أعلى الشاشة."
        "الذاكرة والخصوصية" -> "إعدادات الذاكرة والخصوصية تحتاج إلى ربط مخزن الذاكرة وسياسات الوصول."
        "المظهر" -> "التصميم الحالي يستخدم المظهر الفاتح المطلوب في مواصفات الواجهة."
        "الصوت واللغة" -> "الواجهة الحالية عربية RTL. خدمات الصوت وتبديل اللغة تحتاج إلى ربط فعلي."
        "الاتصال والخادم" -> "الاتصال الحالي يمر عبر ApiClient إلى عنوان API المحلي المعرّف في BuildConfig."
        "حول التطبيق" -> "LAZAYNOVA AI\nPrivate. Autonomous. Yours."
        else -> "هذه الواجهة جاهزة بصرياً، وسيتم ربط الوظيفة الدائمة بالخدمة المناسبة عند تنفيذها."
    }
}
