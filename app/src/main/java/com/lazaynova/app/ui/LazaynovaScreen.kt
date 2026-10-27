package com.lazaynova.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.lazaynova.app.R
import com.lazaynova.app.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LazaynovaScreen() {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var showTasksSheet by remember { mutableStateOf(false) }
    var inputText by remember { mutableStateOf("") }
    
    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                modifier = Modifier.width(310.dp),
                drawerContainerColor = SurfaceWhite
            ) {
                SidebarContent()
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
                        IconButton(onClick = { }) {
                            Icon(Icons.Default.MoreVert, contentDescription = "More", tint = TextDark)
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
                    onSendClick = { inputText = "" }
                )
            }
        ) { paddingValues ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(horizontal = 24.dp),
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
                Text("مرحباً بك في Lazaynova 👋", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextDark)
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    "أنا مساعدك الذكي، جاهز لمساعدتك في أي شيء تخيله أو تحتاجه.",
                    fontSize = 16.sp,
                    color = TextGray,
                    textAlign = TextAlign.Center
                )
            }

            if (showTasksSheet) {
                ModalBottomSheet(
                    onDismissRequest = { showTasksSheet = false },
                    containerColor = SurfaceWhite
                ) {
                    TasksBottomSheetContent(onDismiss = { showTasksSheet = false })
                }
            }
        }
    }
}

@Composable
fun ChatInputArea(
    inputText: String,
    onTextChange: (String) -> Unit,
    onPlusClick: () -> Unit,
    onSendClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(BackgroundLight)
            .navigationBarsPadding()
            .padding(horizontal = 8.dp, vertical = 12.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(30.dp))
                .background(SurfaceWhite)
                .padding(horizontal = 4.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onPlusClick) {
                Icon(Icons.Default.Add, contentDescription = "Add Task", tint = TextGray)
            }

            TextField(
                value = inputText,
                onValueChange = onTextChange,
                placeholder = { Text("اسأل Lazaynova...", color = TextGray, fontSize = 15.sp) },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent
                ),
                modifier = Modifier.weight(1f)
            )

            IconButton(onClick = { }) {
                Icon(Icons.Outlined.Mic, contentDescription = "Voice", tint = TextGray, modifier = Modifier.size(22.dp))
            }
            IconButton(onClick = { }) {
                Icon(Icons.Outlined.Call, contentDescription = "Call", tint = TextGray, modifier = Modifier.size(22.dp))
            }

            FloatingActionButton(
                onClick = onSendClick,
                containerColor = PurplePrimary,
                shape = CircleShape,
                modifier = Modifier.size(44.dp)
            ) {
                Icon(Icons.Default.Send, contentDescription = "Send", tint = Color.White, modifier = Modifier.size(20.dp))
            }
        }
        
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "قد يخطئ الذكاء الاصطناعي، يرجى التحقق من المعلومات المهمة.",
            fontSize = 11.sp,
            color = TextGray,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center
        )
    }
}

@Composable
fun SidebarContent() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(BackgroundLight)
                .clickable { }
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.AccountCircle, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(36.dp))
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text("تسجيل الدخول", fontWeight = FontWeight.Bold, color = TextDark, fontSize = 16.sp)
                Text("بواسطة حساب Google", color = TextGray, fontSize = 12.sp)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = "",
            onValueChange = {},
            placeholder = { Text("بحث...", color = TextGray) },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = TextGray) },
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp)),
            colors = OutlinedTextFieldDefaults.colors(
                unfocusedBorderColor = Color.Transparent,
                focusedBorderColor = PurplePrimary,
                unfocusedContainerColor = BackgroundLight,
                focusedContainerColor = BackgroundLight
            )
        )

        Spacer(modifier = Modifier.height(16.dp))

        SidebarItem(Icons.Outlined.ChatBubbleOutline, "دردشة جديدة")
        SidebarItem(Icons.Outlined.History, "المحادثات")
        SidebarItem(Icons.Outlined.MenuBook, "المكتبة", badge = true)
        SidebarItem(Icons.Outlined.Image, "الوسائط", badge = true)
        SidebarItem(Icons.Outlined.Description, "المستندات")
        SidebarItem(Icons.Outlined.CalendarToday, "جدولة")

        Divider(modifier = Modifier.padding(vertical = 12.dp), color = BackgroundLight)

        Text("الإعدادات الأساسية", color = TextGray, fontSize = 12.sp, modifier = Modifier.padding(bottom = 8.dp))
        SidebarItem(Icons.Outlined.WbSunny, "المظهر")
        SidebarItem(Icons.Outlined.Language, "اللغة")
        SidebarItem(Icons.Outlined.VolumeUp, "صوت الوكيل")
        SidebarItem(Icons.Outlined.Notifications, "الإشعارات")

        Divider(modifier = Modifier.padding(vertical = 12.dp), color = BackgroundLight)

        Text("المزايا المتقدمة", color = TextGray, fontSize = 12.sp, modifier = Modifier.padding(bottom = 8.dp))
        SidebarItem(Icons.Outlined.Group, "الوكلاء")
        SidebarItem(Icons.Outlined.Memory, "الذاكرة")
        SidebarItem(Icons.Outlined.Extension, "التكاملات")
        SidebarItem(Icons.Outlined.Shield, "الأمان والخصوصية")
        SidebarItem(Icons.Outlined.BarChart, "السجلات والتحليلات")

        Spacer(modifier = Modifier.height(24.dp))
        
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(BackgroundLight)
                .clickable { }
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.Star, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(24.dp))
            Spacer(modifier = Modifier.width(12.dp))
            Text("Lazaynova Core", fontWeight = FontWeight.Bold, color = TextDark, fontSize = 14.sp)
        }
        Spacer(modifier = Modifier.height(8.dp))
        SidebarItem(Icons.Outlined.Person, "الحساب والاشتراكات")
        
        Spacer(modifier = Modifier.height(16.dp))
        Text("الإصدار 0.1", color = TextGray, fontSize = 12.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
    }
}

@Composable
fun SidebarItem(icon: ImageVector, title: String, badge: Boolean = false) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable { }
            .padding(vertical = 12.dp, horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = TextDark, modifier = Modifier.size(22.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Text(title, fontSize = 16.sp, color = TextDark, modifier = Modifier.weight(1f))
        if (badge) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(PurplePrimary)
            )
        }
    }
}

@Composable
fun TasksBottomSheetContent(onDismiss: () -> Unit) {
    Column(modifier = Modifier.padding(16.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Spacer(modifier = Modifier.size(24.dp))
            Text("اختيار المهام", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = TextDark)
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, contentDescription = "Close", tint = TextGray)
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TaskCard(Icons.Outlined.Description, "ملفات", Modifier.weight(1f))
            TaskCard(Icons.Outlined.PhotoCamera, "كاميرا", Modifier.weight(1f))
            TaskCard(Icons.Outlined.Image, "صورة", Modifier.weight(1f))
        }
        Spacer(modifier = Modifier.height(8.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TaskCard(Icons.Outlined.Palette, "إنشاء صور", Modifier.weight(1f))
            TaskCard(Icons.Outlined.Videocam, "فيديو (Veo)", Modifier.weight(1f))
            TaskCard(Icons.Outlined.MusicNote, "توليد الموسيقى", Modifier.weight(1f))
            TaskCard(Icons.Outlined.Code, "Canvays", Modifier.weight(1f))
        }
        Spacer(modifier = Modifier.height(8.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TaskCard(Icons.Outlined.Search, "Deep Research", Modifier.weight(1f))
            TaskCard(Icons.Outlined.School, "التعلم الموجه", Modifier.weight(1f))
            TaskCard(Icons.Outlined.Star, "الركائز الموسيقية", Modifier.weight(1f))
            TaskCard(Icons.Outlined.Apps, "المزيد", Modifier.weight(1f))
        }
        
        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
fun TaskCard(icon: ImageVector, title: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(BackgroundLight)
            .clickable { }
            .padding(vertical = 16.dp, horizontal = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(icon, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(28.dp))
        Spacer(modifier = Modifier.height(8.dp))
        Text(title, fontSize = 12.sp, color = TextDark, textAlign = TextAlign.Center, maxLines = 1)
    }
}
