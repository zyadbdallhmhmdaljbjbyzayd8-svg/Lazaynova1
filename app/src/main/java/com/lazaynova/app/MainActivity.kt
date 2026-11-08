package com.lazaynova.app

import android.content.ActivityNotFoundException
import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch

private val Night = Color(0xFF070A14)
private val Panel = Color(0xFF101526)
private val PanelLight = Color(0xFF171F35)
private val Purple = Color(0xFF8755FF)
private val Blue = Color(0xFF398BFF)
private val White = Color(0xFFF4F5FF)
private val Muted = Color(0xFF9AA5BD)
private val BorderColor = Color(0xFF252F49)

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            LazaynovaTheme {
                LazaynovaApplication()
            }
        }
    }
}

@Composable
private fun LazaynovaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Purple,
            secondary = Blue,
            background = Night,
            surface = Panel,
            onPrimary = Color.White,
            onBackground = White,
            onSurface = White
        ),
        content = content
    )
}

private data class ToolEntry(
    val title: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val engine: String? = null,
    val prompt: String? = null,
    val action: String? = null
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LazaynovaApplication(
    vm: ChatViewModel = viewModel()
) {
    val state by vm.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val sheetState = rememberModalBottomSheetState(
        skipPartiallyExpanded = true
    )

    var input by remember { mutableStateOf("") }
    var showTools by remember { mutableStateOf(false) }
    var showModelMenu by remember { mutableStateOf(false) }
    var selectedSection by remember { mutableStateOf("الدردشة") }
    var capturedBitmap by remember { mutableStateOf<Bitmap?>(null) }

    val cameraLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.TakePicturePreview()
    ) { bitmap ->
        capturedBitmap = bitmap
        if (bitmap != null) {
            vm.addLocalMessage(
                "تم التقاط صورة بالكاميرا. ملاحظة: الخادم الحالي لا يوفّر واجهة رفع صور."
            )
        }
    }

    val contentLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            vm.addLocalMessage(
                "تم اختيار الملف: ${uri.lastPathSegment ?: uri.toString()}. لم يتم رفع محتواه؛ واجهة الخادم الحالية تستقبل النص فقط."
            )
        }
    }

    val speechLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val spoken = result.data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()

        if (!spoken.isNullOrBlank()) {
            input = spoken
        }
    }

    val tools = remember {
        listOf(
            ToolEntry("صورة", Icons.Default.Image, action = "image"),
            ToolEntry("كاميرا", Icons.Default.CameraAlt, action = "camera"),
            ToolEntry("ملفات", Icons.Default.AttachFile, action = "files"),
            ToolEntry("إنشاء صور", Icons.Default.AutoAwesome, "image", "أنشئ تصوراً نصياً مفصلاً لصورة حسب طلبي: "),
            ToolEntry("فيديو Veo", Icons.Default.VideoLibrary, "video", "خطط لإنشاء فيديو حول: "),
            ToolEntry("مكالمة ذكية", Icons.Default.Phone, "agent", "ابدأ جلسة تفاعل صوتية ذكية. جهّز أسئلة التفاعل حول: "),
            ToolEntry("Deep Research", Icons.Default.Search, "research", "أجرِ بحثاً معمقاً حول: "),
            ToolEntry("Guided Learning", Icons.Default.School, "chat", "علّمني خطوة بخطوة: "),
            ToolEntry("Musical AI", Icons.Default.MusicNote, "music", "ضع تصوراً موسيقياً حول: "),
            ToolEntry("Generative Text", Icons.Default.Description, "chat", "اكتب محتوى احترافياً حول: "),
            ToolEntry("Voice of Agent", Icons.Default.GraphicEq, "agent", "حلّل طلب التفاعل الصوتي التالي: "),
            ToolEntry("اللغة", Icons.Default.Language, "chat", "ساعدني في الترجمة أو تعلم اللغة: "),
            ToolEntry("الإشعارات", Icons.Default.Notifications, "chat", "ساعدني في تنظيم الإشعارات والمهام: "),
            ToolEntry("Smart Agents", Icons.Default.SmartToy, "agent", "حلّل المهمة التالية وخطط لتنفيذها بواسطة الوكيل الذكي: ")
        )
    }

    fun sendPrompt(
        prompt: String,
        engine: String? = null
    ) {
        if (prompt.isBlank()) return
        vm.sendMessage(prompt, engine)
        input = ""
    }

    CompositionLocalProvider(
        LocalLayoutDirection provides LayoutDirection.Rtl
    ) {
        ModalNavigationDrawer(
            drawerState = drawerState,
            drawerContent = {
                ModalDrawerSheet(
                    drawerContainerColor = Panel,
                    modifier = Modifier.width(290.dp)
                ) {
                    LeftSidebar(
                        selected = selectedSection,
                        onSelect = {
                            selectedSection = it
                            scope.launch { drawerState.close() }
                            if (it == "دردشة جديدة") vm.newChat()
                            if (it == "حذف السجلات بالكامل") vm.deleteChatHistory()
                        }
                    )
                }
            },
            gesturesEnabled = true
        ) {
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Night)
            ) {
                val wide = maxWidth >= 1150.dp
                val medium = maxWidth >= 780.dp

                if (wide) {
                    Row(Modifier.fillMaxSize()) {
                        RightControlPanel(
                            modifier = Modifier
                                .width(260.dp)
                                .fillMaxHeight()
                        )

                        CenterWorkspace(
                            modifier = Modifier
                                .weight(1f)
                                .fillMaxHeight(),
                            state = state,
                            input = input,
                            onInput = { input = it },
                            onSend = { sendPrompt(input) },
                            onOpenTools = { showTools = true },
                            onOpenDrawer = {
                                scope.launch { drawerState.open() }
                            },
                            onOpenModelMenu = { showModelMenu = true },
                            showModelMenu = showModelMenu,
                            onDismissModelMenu = { showModelMenu = false },
                            onSelectModel = { vm.selectModel(it) },
                            onMic = {
                                launchSpeech(speechLauncher = { intent ->
                                    try {
                                        speechLauncher.launch(intent)
                                    } catch (_: ActivityNotFoundException) {
                                        vm.addLocalMessage(
                                            "لا يوجد تطبيق للتعرف على الكلام مثبت على الجهاز."
                                        )
                                    }
                                })
                            },
                            bitmap = capturedBitmap,
                            onShare = { shareText(context, it) }
                        )

                        LeftSidebar(
                            selected = selectedSection,
                            modifier = Modifier
                                .width(270.dp)
                                .fillMaxHeight(),
                            onSelect = {
                                selectedSection = it
                                if (it == "دردشة جديدة") vm.newChat()
                                if (it == "حذف السجلات بالكامل") vm.deleteChatHistory()
                            }
                        )
                    }
                } else {
                    Row(Modifier.fillMaxSize()) {
                        if (medium) {
                            RightControlPanel(
                                modifier = Modifier
                                    .width(220.dp)
                                    .fillMaxHeight()
                            )
                        }

                        CenterWorkspace(
                            modifier = Modifier
                                .weight(1f)
                                .fillMaxHeight(),
                            state = state,
                            input = input,
                            onInput = { input = it },
                            onSend = { sendPrompt(input) },
                            onOpenTools = { showTools = true },
                            onOpenDrawer = {
                                scope.launch { drawerState.open() }
                            },
                            onOpenModelMenu = { showModelMenu = true },
                            showModelMenu = showModelMenu,
                            onDismissModelMenu = { showModelMenu = false },
                            onSelectModel = { vm.selectModel(it) },
                            onMic = {
                                launchSpeech(speechLauncher = { intent ->
                                    try {
                                        speechLauncher.launch(intent)
                                    } catch (_: ActivityNotFoundException) {
                                        vm.addLocalMessage(
                                            "لا يوجد تطبيق للتعرف على الكلام مثبت على الجهاز."
                                        )
                                    }
                                })
                            },
                            bitmap = capturedBitmap,
                            onShare = { shareText(context, it) }
                        )
                    }
                }
            }
        }
    }

    if (showTools) {
        ModalBottomSheet(
            onDismissRequest = { showTools = false },
            sheetState = sheetState,
            containerColor = Panel,
            contentColor = White,
            dragHandle = {
                BottomSheetDefaults.DragHandle(color = Muted)
            }
        ) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 18.dp)
                    .padding(bottom = 28.dp)
            ) {
                Text(
                    "لوحة المهام والأدوات والميزات الكاملة",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = White
                )

                Spacer(Modifier.height(18.dp))

                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    modifier = Modifier.heightIn(max = 480.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    gridItems(tools) { tool ->
                        ToolTile(tool) {
                            showTools = false

                            when (tool.action) {
                                "camera" -> cameraLauncher.launch(null)
                                "files" -> contentLauncher.launch("*/*")
                                "image" -> contentLauncher.launch("image/*")
                                else -> {
                                    val prompt = tool.prompt.orEmpty()
                                    input = prompt
                                    if (tool.engine != null) {
                                        vm.sendMessage(
                                            prompt.trim(),
                                            tool.engine
                                        )
                                        input = ""
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun launchSpeech(
    speechLauncher: (Intent) -> Unit
) {
    val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
        putExtra(
            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        )
        putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ar")
        putExtra(RecognizerIntent.EXTRA_PROMPT, "تحدث إلى Lazaynova")
    }
    speechLauncher(intent)
}

@Composable
private fun CenterWorkspace(
    modifier: Modifier,
    state: ChatUiState,
    input: String,
    onInput: (String) -> Unit,
    onSend: () -> Unit,
    onOpenTools: () -> Unit,
    onOpenDrawer: () -> Unit,
    onOpenModelMenu: () -> Unit,
    showModelMenu: Boolean,
    onDismissModelMenu: () -> Unit,
    onSelectModel: (String) -> Unit,
    onMic: () -> Unit,
    bitmap: Bitmap?,
    onShare: (String) -> Unit
) {
    Column(
        modifier
            .background(Night)
            .padding(horizontal = 18.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(66.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onOpenDrawer) {
                Icon(Icons.Default.Menu, null, tint = White)
            }

            LazaynovaMark(size = 34.dp)

            Spacer(Modifier.width(10.dp))

            Column(Modifier.weight(1f)) {
                Text(
                    "LAZAYNOVA AI",
                    color = White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
                Text(
                    "Private. Autonomous. Yours.",
                    color = Muted,
                    fontSize = 10.sp
                )
            }

            Box {
                OutlinedButton(
                    onClick = onOpenModelMenu,
                    contentPadding = PaddingValues(
                        horizontal = 12.dp,
                        vertical = 6.dp
                    )
                ) {
                    Icon(
                        Icons.Default.AutoAwesome,
                        null,
                        tint = Purple,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(state.selectedModel, color = White)
                }

                DropdownMenu(
                    expanded = showModelMenu,
                    onDismissRequest = onDismissModelMenu,
                    modifier = Modifier.background(Panel)
                ) {
                    listOf(
                        "4LZ",
                        "4.5LZ",
                        "5LZ",
                        "6LZ",
                        "6.5LZ",
                        "7LZ",
                        "8LZ"
                    ).forEach { model ->
                        DropdownMenuItem(
                            text = {
                                Text(model, color = White)
                            },
                            onClick = {
                                onSelectModel(model)
                                onDismissModelMenu()
                            }
                        )
                    }
                }
            }
        }

        HorizontalDivider(color = BorderColor)

        if (state.messages.isEmpty()) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                LazaynovaMark(size = 124.dp)

                Spacer(Modifier.height(26.dp))

                Text(
                    "مرحباً بك في Lazaynova",
                    color = White,
                    fontSize = 25.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )

                Spacer(Modifier.height(12.dp))

                Text(
                    "أنا مساعدك الذكي، جاهز لمساعدتك في أي شيء تخيله أو تحتاجه.",
                    color = Muted,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center,
                    lineHeight = 23.sp,
                    modifier = Modifier.widthIn(max = 440.dp)
                )

                Spacer(Modifier.height(24.dp))

                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    SuggestionChip(
                        onClick = { onInput("ساعدني في التخطيط لمشروعي") },
                        label = { Text("التخطيط") }
                    )
                    SuggestionChip(
                        onClick = { onInput("ابحث لي بعمق عن موضوع جديد") },
                        label = { Text("البحث") }
                    )
                    SuggestionChip(
                        onClick = { onInput("اكتب لي كوداً برمجياً") },
                        label = { Text("البرمجة") }
                    )
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                reverseLayout = false,
                contentPadding = PaddingValues(
                    vertical = 18.dp,
                    horizontal = 4.dp
                ),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                items(
                    state.messages,
                    key = { it.id }
                ) { message ->
                    MessageCard(
                        message = message,
                        onShare = onShare
                    )
                }

                if (state.isLoading) {
                    item {
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = Purple,
                                strokeWidth = 2.dp
                            )
                            Spacer(Modifier.width(12.dp))
                            Text(
                                "Lazaynova يعمل على طلبك...",
                                color = Muted,
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }
        }

        if (bitmap != null) {
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = "الصورة الملتقطة",
                modifier = Modifier
                    .size(76.dp)
                    .clip(RoundedCornerShape(12.dp))
            )
            Spacer(Modifier.height(8.dp))
        }

        CommandBar(
            value = input,
            onValueChange = onInput,
            onSend = onSend,
            onTools = onOpenTools,
            onMic = onMic
        )

        Spacer(Modifier.height(12.dp))
    }
}

@Composable
private fun CommandBar(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
    onTools: () -> Unit,
    onMic: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(16.dp, RoundedCornerShape(24.dp))
            .background(Panel, RoundedCornerShape(24.dp))
            .border(1.dp, BorderColor, RoundedCornerShape(24.dp))
            .padding(horizontal = 8.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onTools) {
            Icon(
                Icons.Default.Add,
                contentDescription = "المرفقات والأدوات",
                tint = Purple
            )
        }

        IconButton(onClick = onMic) {
            Icon(
                Icons.Default.Mic,
                contentDescription = "الميكروفون",
                tint = Muted
            )
        }

        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.weight(1f),
            placeholder = {
                Text(
                    "اسأل Lazaynova...",
                    color = Muted,
                    fontSize = 14.sp
                )
            },
            maxLines = 4,
            shape = RoundedCornerShape(18.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Color.Transparent,
                unfocusedBorderColor = Color.Transparent,
                focusedTextColor = White,
                unfocusedTextColor = White,
                cursorColor = Purple,
                focusedContainerColor = Color.Transparent,
                unfocusedContainerColor = Color.Transparent
            ),
            keyboardOptions = KeyboardOptions(
                imeAction = ImeAction.Send
            ),
            keyboardActions = KeyboardActions(
                onSend = { onSend() }
            )
        )

        IconButton(
            onClick = onSend,
            enabled = value.isNotBlank()
        ) {
            Icon(
                Icons.Default.Send,
                contentDescription = "إرسال",
                tint = if (value.isNotBlank()) Purple else Muted
            )
        }
    }
}

@Composable
private fun MessageCard(
    message: LazaynovaMessage,
    onShare: (String) -> Unit
) {
    val clipboard = LocalClipboardManager.current

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (message.isUser) {
            Alignment.Start
        } else {
            Alignment.End
        }
    ) {
        Surface(
            color = if (message.isUser) PanelLight else Panel,
            shape = RoundedCornerShape(18.dp),
            border = androidx.compose.foundation.BorderStroke(
                1.dp,
                BorderColor
            ),
            modifier = Modifier.widthIn(max = 680.dp)
        ) {
            Column(Modifier.padding(14.dp)) {
                Text(
                    message.text,
                    color = White,
                    fontSize = 14.sp,
                    lineHeight = 23.sp
                )

                if (message.model.isNotBlank()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        message.model,
                        color = Muted,
                        fontSize = 10.sp
                    )
                }
            }
        }

        Row {
            IconButton(
                onClick = {
                    clipboard.setText(
                        androidx.compose.ui.text.AnnotatedString(message.text)
                    )
                },
                modifier = Modifier.size(34.dp)
            ) {
                Icon(
                    Icons.Default.ContentCopy,
                    "نسخ",
                    tint = Muted,
                    modifier = Modifier.size(16.dp)
                )
            }

            IconButton(
                onClick = { onShare(message.text) },
                modifier = Modifier.size(34.dp)
            ) {
                Icon(
                    Icons.Default.Share,
                    "مشاركة",
                    tint = Muted,
                    modifier = Modifier.size(16.dp)
                )
            }
        }
    }
}

@Composable
private fun LeftSidebar(
    selected: String,
    modifier: Modifier = Modifier,
    onSelect: (String) -> Unit
) {
    val mainItems = listOf(
        "دردشة جديدة" to Icons.Default.Add,
        "المحادثات" to Icons.Default.Chat,
        "المكتبة" to Icons.Default.LibraryBooks,
        "الوسائط" to Icons.Default.Image,
        "المستندات" to Icons.Default.Description,
        "جدولة" to Icons.Default.CalendarToday
    )

    val settings = listOf(
        "المظهر" to Icons.Default.LightMode,
        "اللغة" to Icons.Default.Language,
        "صوت الوكيل" to Icons.Default.GraphicEq,
        "الإشعارات" to Icons.Default.Notifications
    )

    val advanced = listOf(
        "الوكلاء" to Icons.Default.SmartToy,
        "الذاكرة" to Icons.Default.Memory,
        "التكاملات" to Icons.Default.Extension,
        "الأمان والخصوصية" to Icons.Default.Security,
        "السجلات والتحليلات" to Icons.Default.Analytics
    )

    Column(
        modifier
            .background(Panel)
            .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LazaynovaMark(38.dp)
            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    "LAZAYNOVA",
                    color = White,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "Private. Autonomous. Yours.",
                    color = Muted,
                    fontSize = 9.sp
                )
            }
        }

        Spacer(Modifier.height(22.dp))

        OutlinedTextField(
            value = "",
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            enabled = false,
            placeholder = {
                Text("بحث", color = Muted)
            },
            leadingIcon = {
                Icon(Icons.Default.Search, null, tint = Muted)
            },
            singleLine = true,
            shape = RoundedCornerShape(14.dp)
        )

        Spacer(Modifier.height(18.dp))

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            item { SidebarHeader("مساحة العمل") }
            items(mainItems) { item ->
                SidebarItem(
                    item.first,
                    item.second,
                    selected == item.first
                ) { onSelect(item.first) }
            }

            item {
                Spacer(Modifier.height(12.dp))
                SidebarHeader("الإعدادات الأساسية")
            }

            items(settings) { item ->
                SidebarItem(
                    item.first,
                    item.second,
                    selected == item.first
                ) { onSelect(item.first) }
            }

            item {
                Spacer(Modifier.height(12.dp))
                SidebarHeader("المميزات المتقدمة")
            }

            items(advanced) { item ->
                SidebarItem(
                    item.first,
                    item.second,
                    selected == item.first
                ) { onSelect(item.first) }
            }

            item {
                SidebarItem(
                    "حذف السجلات بالكامل",
                    Icons.Default.Delete,
                    false
                ) { onSelect("حذف السجلات بالكامل") }
            }
        }

        HorizontalDivider(color = BorderColor)

        Spacer(Modifier.height(12.dp))

        Surface(
            color = PanelLight,
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(13.dp)) {
                Text(
                    "LAZAYNOVA CORE",
                    color = Purple,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
                Text(
                    "الموكل الرئيسي",
                    color = White,
                    fontSize = 12.sp
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    "زيد الجبيجي",
                    color = White,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    "الحساب والاشتراكات · الإصدار 0.1",
                    color = Muted,
                    fontSize = 10.sp
                )
            }
        }
    }
}

@Composable
private fun SidebarHeader(text: String) {
    Text(
        text,
        color = Muted,
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(
            start = 8.dp,
            top = 7.dp,
            bottom = 6.dp
        )
    )
}

@Composable
private fun SidebarItem(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    selected: Boolean,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(
                if (selected) Color(0xFF252044) else Color.Transparent
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            icon,
            null,
            tint = if (selected) Purple else Muted,
            modifier = Modifier.size(18.dp)
        )
        Spacer(Modifier.width(11.dp))
        Text(
            title,
            color = if (selected) White else Muted,
            fontSize = 12.sp
        )
    }
}

@Composable
private fun RightControlPanel(modifier: Modifier = Modifier) {
    Column(
        modifier
            .background(Panel)
            .padding(15.dp)
    ) {
        Surface(
            color = PanelLight,
            shape = RoundedCornerShape(17.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Default.AccountCircle,
                        null,
                        tint = Purple,
                        modifier = Modifier.size(30.dp)
                    )
                    Spacer(Modifier.width(9.dp))
                    Column {
                        Text(
                            "زيد الجبيجي",
                            color = White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                        Text(
                            "حساب مجاني",
                            color = Muted,
                            fontSize = 11.sp
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))
                Text(
                    "إدارة الحساب",
                    color = Purple,
                    fontSize = 11.sp
                )
            }
        }

        Spacer(Modifier.height(20.dp))
        SidebarHeader("المكونات الإضافية")

        listOf(
            "الوكيل الذكي" to Icons.Default.SmartToy,
            "رفع الصور" to Icons.Default.Image,
            "رفع الملفات" to Icons.Default.AttachFile
        ).forEach {
            CompactFeature(it.first, it.second)
        }

        Spacer(Modifier.height(18.dp))
        SidebarHeader("المميزات والمهام الرئيسية")

        listOf(
            "تحليل الملاحظات الصوتية" to Icons.Default.GraphicEq,
            "مكالمات صوتية ومرئية" to Icons.Default.Phone,
            "توليد الموسيقى" to Icons.Default.MusicNote,
            "Code Generation" to Icons.Default.Code,
            "Deep Research" to Icons.Default.Search,
            "التوليد الإبداعي" to Icons.Default.AutoAwesome
        ).forEach {
            CompactFeature(it.first, it.second)
        }

        Spacer(Modifier.height(18.dp))
        SidebarHeader("اختصارات")

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MiniFeature(Icons.Default.MusicNote, "Music")
            MiniFeature(Icons.Default.Code, "Code")
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MiniFeature(Icons.Default.Image, "Photo")
            MiniFeature(Icons.Default.AttachFile, "Files")
        }
    }
}

@Composable
private fun CompactFeature(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector
) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            icon,
            null,
            tint = Purple,
            modifier = Modifier.size(17.dp)
        )
        Spacer(Modifier.width(10.dp))
        Text(
            title,
            color = Muted,
            fontSize = 11.sp
        )
    }
}

@Composable
private fun MiniFeature(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String
) {
    Column(
        modifier = Modifier
            .weight(1f)
            .clip(RoundedCornerShape(12.dp))
            .background(PanelLight)
            .padding(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(icon, null, tint = Purple)
        Spacer(Modifier.height(5.dp))
        Text(label, color = Muted, fontSize = 10.sp)
    }
}

@Composable
private fun ToolTile(
    tool: ToolEntry,
    onClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(PanelLight)
            .clickable(onClick = onClick)
            .padding(vertical = 17.dp, horizontal = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            tool.icon,
            contentDescription = tool.title,
            tint = Purple,
            modifier = Modifier.size(25.dp)
        )
        Spacer(Modifier.height(9.dp))
        Text(
            tool.title,
            color = White,
            fontSize = 10.sp,
            textAlign = TextAlign.Center,
            lineHeight = 15.sp
        )
    }
}

@Composable
private fun LazaynovaMark(size: androidx.compose.ui.unit.Dp) {
    Box(
        modifier = Modifier
            .size(size)
            .shadow(
                elevation = 16.dp,
                shape = RoundedCornerShape(size * 0.28f),
                ambientColor = Purple,
                spotColor = Blue
            )
            .clip(RoundedCornerShape(size * 0.28f))
            .background(
                Brush.linearGradient(
                    listOf(
                        Color(0xFF9A5BFF),
                        Color(0xFF5940D9),
                        Color(0xFF237FEA)
                    )
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Text(
            "L",
            color = Color.White,
            fontSize = (size.value * 0.68f).sp,
            fontWeight = FontWeight.Black
        )
    }
}

private fun shareText(
    context: android.content.Context,
    text: String
) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, text)
    }

    context.startActivity(
        Intent.createChooser(intent, "مشاركة رسالة Lazaynova")
    )
}
