package com.lazaynova.app.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.lazaynova.app.R
import com.lazaynova.app.ui.theme.*
import kotlinx.coroutines.launch

data class ChatMessage(
    val id: String = java.util.UUID.randomUUID().toString(),
    var text: String,
    val isUser: Boolean,
    var imageUri: Uri? = null
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LazaynovaScreen() {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var showTasksSheet by remember { mutableStateOf(false) }
    
    // حالة المحادثة
    val messages = remember { mutableStateListOf<ChatMessage>() }
    var inputText by remember { mutableStateOf("") }
    var editingMessageId by remember { mutableStateOf<String?>(null) }
    var isRecording by remember { mutableStateOf(false) }
    var isCalling by remember { mutableStateOf(false) }

    // منتقي الصور الحقيقي
    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            messages.add(ChatMessage(text = "صورة مرفوعة", isUser = true, imageUri = uri))
            showTasksSheet = false
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(modifier = Modifier.width(310.dp), drawerContainerColor = SurfaceWhite) {
                SidebarContent(
                    onNewChat = {
                        messages.clear()
                        scope.launch { drawerState.close() }
                    }
                )
            }
        }
    ) {
        Scaffold(
            containerColor = BackgroundLight,
            topBar = {
                TopAppBar(
                    title = {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Star, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Lazaynova", fontWeight = FontWeight.Bold, color = TextDark, fontSize = 20.sp)
                        }
                    },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu", tint = TextDark)
                        }
                    },
                    actions = {
                        IconButton(onClick = { messages.clear() }) {
                            Icon(Icons.Default.Add, contentDescription = "New Chat", tint = TextDark)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
                )
            },
            bottomBar = {
                ChatInputArea(
                    inputText = inputText,
                    onTextChange = { inputText = it },
                    onPlusClick = { showTasksSheet = true },
                    isRecording = isRecording,
                    isCalling = isCalling,
                    onMicClick = { isRecording = !isRecording },
                    onCallClick = { isCalling = !isCalling },
                    onSendClick = {
                        if (inputText.isNotBlank()) {
                            if (editingMessageId != null) {
                                val msg = messages.find { it.id == editingMessageId }
                                msg?.text = inputText
                                editingMessageId = null
                            } else {
                                messages.add(ChatMessage(text = inputText, isUser = true))
                            }
                            inputText = ""
                        }
                    }
                )
            }
        ) { paddingValues ->
            if (messages.isEmpty()) {
                Column(
                    modifier = Modifier.fillMaxSize().padding(paddingValues).padding(horizontal = 24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.lazaynova_logo),
                        contentDescription = "Logo",
                        modifier = Modifier.size(160.dp)
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Text("Lazaynova", fontSize = 36.sp, fontWeight = FontWeight.ExtraBold, color = PurplePrimary)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("مرحباً بك 👋", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextDark)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("كيف يمكنني مساعدتك اليوم؟", fontSize = 16.sp, color = TextGray, textAlign = TextAlign.Center)
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(paddingValues).padding(horizontal = 16.dp),
                    reverseLayout = true,
                    contentPadding = PaddingValues(vertical = 16.dp)
                ) {
                    items(messages.reversed()) { message ->
                        MessageBubble(
                            message = message,
                            onEdit = {
                                inputText = message.text
                                editingMessageId = message.id
                            },
                            onDelete = {
                                messages.remove(message)
                                if (editingMessageId == message.id) {
                                    editingMessageId = null
                                    inputText = ""
                                }
                            }
                        )
                    }
                }
            }

            if (showTasksSheet) {
                ModalBottomSheet(onDismissRequest = { showTasksSheet = false }, containerColor = SurfaceWhite) {
                    TasksBottomSheetContent(
                        onDismiss = { showTasksSheet = false },
                        onPickImage = { imagePickerLauncher.launch("image/*") }
                    )
                }
            }
        }
    }
}

@Composable
fun MessageBubble(message: ChatMessage, onEdit: () -> Unit, onDelete: () -> Unit) {
    var showMenu by remember { mutableStateOf(false) }
    
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = if (message.isUser) Arrangement.End else Arrangement.Start
    ) {
        Box {
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = if (message.isUser) PurpleLight else SurfaceWhite),
                modifier = Modifier.clickable { showMenu = true }.widthIn(max = 280.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    if (message.imageUri != null) {
                        AsyncImage(
                            model = message.imageUri,
                            contentDescription = "Uploaded Image",
                            modifier = Modifier.height(150.dp).fillMaxWidth().clip(RoundedCornerShape(8.dp)),
                            contentScale = ContentScale.Crop
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                    }
                    Text(message.text, color = TextDark, fontSize = 16.sp)
                }
            }
            DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                if (message.isUser) {
                    DropdownMenuItem(text = { Text("تعديل") }, onClick = { onEdit(); showMenu = false })
                    DropdownMenuItem(text = { Text("حذف") }, onClick = { onDelete(); showMenu = false })
                }
            }
        }
    }
}

@Composable
fun ChatInputArea(
    inputText: String, onTextChange: (String) -> Unit, onPlusClick: () -> Unit,
    isRecording: Boolean, isCalling: Boolean, onMicClick: () -> Unit, onCallClick: () -> Unit,
    onSendClick: () -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth().background(BackgroundLight).navigationBarsPadding().padding(horizontal = 8.dp, vertical = 12.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(30.dp)).background(SurfaceWhite).padding(horizontal = 4.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onPlusClick) { Icon(Icons.Default.Add, contentDescription = "Add", tint = TextGray) }
            
            TextField(
                value = inputText,
                onValueChange = onTextChange,
                placeholder = { Text("اسأل Lazaynova...", color = TextGray, fontSize = 15.sp) },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent, unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent
                ),
                modifier = Modifier.weight(1f)
            )

            IconButton(onClick = onMicClick) {
                Icon(Icons.Outlined.Mic, contentDescription = "Voice", tint = if (isRecording) Color.Red else TextGray, modifier = Modifier.size(22.dp))
            }
            IconButton(onClick = onCallClick) {
                Icon(Icons.Outlined.Call, contentDescription = "Call", tint = if (isCalling) Color.Green else TextGray, modifier = Modifier.size(22.dp))
            }

            FloatingActionButton(
                onClick = onSendClick,
                containerColor = PurplePrimary, shape = CircleShape,
                modifier = Modifier.size(44.dp)
            ) {
                Icon(Icons.Default.Send, contentDescription = "Send", tint = Color.White, modifier = Modifier.size(20.dp))
            }
        }
        if (isRecording) Text("جاري التسجيل الصوتي...", color = Color.Red, fontSize = 12.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
    }
}

@Composable
fun SidebarContent(onNewChat: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Row(modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(BackgroundLight).clickable { }.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.AccountCircle, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(36.dp))
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text("تسجيل الدخول", fontWeight = FontWeight.Bold, color = TextDark, fontSize = 16.sp)
                Text("بواسطة حساب Google", color = TextGray, fontSize = 12.sp)
            }
        }
        Spacer(modifier = Modifier.height(16.dp))
        SidebarItem(Icons.Outlined.ChatBubbleOutline, "دردشة جديدة", onClick = onNewChat)
        SidebarItem(Icons.Outlined.History, "المحادثات", onClick = {})
        SidebarItem(Icons.Outlined.MenuBook, "المكتبة", badge = true, onClick = {})
        
        Divider(modifier = Modifier.padding(vertical = 12.dp), color = BackgroundLight)
        Text("الإعدادات", color = TextGray, fontSize = 12.sp, modifier = Modifier.padding(bottom = 8.dp))
        SidebarItem(Icons.Outlined.WbSunny, "المظهر", onClick = {})
        SidebarItem(Icons.Outlined.Language, "اللغة", onClick = {})
        
        Spacer(modifier = Modifier.height(24.dp))
        Text("الإصدار 0.1", color = TextGray, fontSize = 12.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
    }
}

@Composable
fun SidebarItem(icon: ImageVector, title: String, badge: Boolean = false, onClick: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).clickable { onClick() }.padding(vertical = 12.dp, horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = TextDark, modifier = Modifier.size(22.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Text(title, fontSize = 16.sp, color = TextDark, modifier = Modifier.weight(1f))
        if (badge) Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(PurplePrimary))
    }
}

@Composable
fun TasksBottomSheetContent(onDismiss: () -> Unit, onPickImage: () -> Unit) {
    Column(modifier = Modifier.padding(16.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Spacer(modifier = Modifier.size(24.dp))
            Text("اختيار المهام", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = TextDark)
            IconButton(onClick = onDismiss) { Icon(Icons.Default.Close, contentDescription = "Close", tint = TextGray) }
        }
        Spacer(modifier = Modifier.height(16.dp))

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TaskCard(Icons.Outlined.Description, "ملفات", Modifier.weight(1f), onPickImage)
            TaskCard(Icons.Outlined.PhotoCamera, "كاميرا", Modifier.weight(1f), onPickImage)
            TaskCard(Icons.Outlined.Image, "صورة", Modifier.weight(1f), onPickImage)
        }
        Spacer(modifier = Modifier.height(8.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TaskCard(Icons.Outlined.Palette, "إنشاء صور", Modifier.weight(1f), {})
            TaskCard(Icons.Outlined.Videocam, "فيديو (Veo)", Modifier.weight(1f), {})
        }
        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
fun TaskCard(icon: ImageVector, title: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier = modifier.clip(RoundedCornerShape(12.dp)).background(BackgroundLight).clickable { onClick() }.padding(vertical = 16.dp, horizontal = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(icon, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(28.dp))
        Spacer(modifier = Modifier.height(8.dp))
        Text(title, fontSize = 12.sp, color = TextDark, textAlign = TextAlign.Center, maxLines = 1)
    }
}
