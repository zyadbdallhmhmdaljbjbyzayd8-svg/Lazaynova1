package com.lazaynova.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
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
    var showEngineMenu by remember { mutableStateOf(false) }
    var showBottomSheet by remember { mutableStateOf(false) }
    var selectedEngine by remember { mutableStateOf("L4.5") }
    var inputText by remember { mutableStateOf("") }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(modifier = Modifier.width(300.dp)) {
                SideMenuContent()
            }
        }
    ) {
        Scaffold(
            containerColor = BackgroundLight,
            topBar = {
                TopAppBar(
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Lazaynova", fontWeight = FontWeight.Bold, color = PurplePrimary, fontSize = 20.sp)
                            Spacer(modifier = Modifier.width(8.dp))
                            // Engine Selector Pill
                            Box {
                                Row(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(20.dp))
                                        .background(PurpleLight)
                                        .clickable { showEngineMenu = true }
                                        .padding(horizontal = 10.dp, vertical = 4.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(Icons.Default.Build, null, modifier = Modifier.size(14.dp), tint = PurplePrimary)
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(selectedEngine, color = PurplePrimary, fontSize = 12.sp)
                                    Icon(Icons.Default.ArrowDropDown, null, tint = PurplePrimary)
                                }
                                DropdownMenu(expanded = showEngineMenu, onDismissRequest = { showEngineMenu = false }) {
                                    listOf("Lazaynova 4.5", "Lazaynova 5", "Lazaynova 4", "Lazaynova 3").forEach { engine ->
                                        DropdownMenuItem(
                                            text = { Text(engine) },
                                            onClick = { selectedEngine = engine; showEngineMenu = false }
                                        )
                                    }
                                }
                            }
                        }
                    },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu", tint = TextDark)
                        }
                    },
                    actions = {
                        IconButton(onClick = { /* Close action */ }) {
                            Icon(Icons.Default.Close, contentDescription = "Close", tint = TextDark)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = BackgroundLight)
                )
            },
            bottomBar = {
                ChatInputBar(
                    inputText = inputText,
                    onTextChange = { inputText = it },
                    onPlusClick = { showBottomSheet = true }
                )
            }
        ) { paddingValues ->
            // Main Chat Area
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(horizontal = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                // الشعار (تم تصغيره هنا ليكون 120dp)
                Image(
                    painter = painterResource(id = R.drawable.lazaynova_logo), // تأكد من وجود الصورة في res/drawable
                    contentDescription = "Lazaynova Logo",
                    modifier = Modifier.size(120.dp)
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text("Lazaynova", fontSize = 28.sp, fontWeight = FontWeight.Bold, color = PurplePrimary)
                Text("— الزنوفا —", fontSize = 16.sp, color = TextGray)
                Spacer(modifier = Modifier.height(32.dp))
                Text("كيف أستطيع مساعدتك؟", fontSize = 22.sp, fontWeight = FontWeight.Medium, color = TextDark)
                Spacer(modifier = Modifier.height(8.dp))
                Text("اسأل، خطط، أنشئ، أو ابدأ مشروع جديد.", fontSize = 14.sp, color = TextGray)
            }

            // Tasks Bottom Sheet
            if (showBottomSheet) {
                ModalBottomSheet(onDismissRequest = { showBottomSheet = false }) {
                    TasksMenuContent()
                }
            }
        }
    }
}

@Composable
fun ChatInputBar(inputText: String, onTextChange: (String) -> Unit, onPlusClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(BackgroundLight)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(30.dp))
                .background(SurfaceWhite)
                .padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onPlusClick) {
                Icon(Icons.Default.Add, contentDescription = "Add", tint = PurplePrimary)
            }
            TextField(
                value = inputText,
                onValueChange = onTextChange,
                placeholder = { Text("اكتب رسالتك هنا...", color = TextGray) },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent
                ),
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = { }) { Icon(Icons.Default.Mic, null, tint = TextGray) }
            IconButton(onClick = { }) { Icon(Icons.Default.Call, null, tint = TextGray) }
        }
        Spacer(modifier = Modifier.width(8.dp))
        FloatingActionButton(
            onClick = { },
            containerColor = PurplePrimary,
            shape = CircleShape,
            modifier = Modifier.size(48.dp)
        ) {
            Icon(Icons.Default.Send, contentDescription = "Send", tint = Color.White)
        }
    }
}

@Composable
fun SideMenuContent() {
    Column(modifier = Modifier.padding(16.dp)) {
        Text("Lazaynova", fontWeight = FontWeight.Bold, color = PurplePrimary, fontSize = 24.sp)
        Text("— الزنوفا —", color = TextGray, fontSize = 14.sp)
        Spacer(modifier = Modifier.height(24.dp))
        
        MenuItem(Icons.Default.Add, "محادثة جديدة")
        MenuItem(Icons.Default.Search, "البحث في المحادثات")
        MenuItem(Icons.Default.History, "المحادثات الأخيرة")
        MenuItem(Icons.Default.Folder, "المشاريع")
        MenuItem(Icons.Default.Person, "فريق الوكلاء")
        
        Divider(modifier = Modifier.padding(vertical = 12.dp))
        Text("المزايا", color = TextGray, fontSize = 12.sp)
        MenuItem(Icons.Default.Image, "إنشاء الصور")
        MenuItem(Icons.Default.Videocam, "إنشاء الفيديو")
        MenuItem(Icons.Default.MusicNote, "إنشاء الموسيقى")
        MenuItem(Icons.Default.Code, "البرمجة")
        MenuItem(Icons.Default.PhoneAndroid, "إنشاء تطبيقات")
        MenuItem(Icons.Default.Language, "إنشاء مواقع ويب")
        
        Divider(modifier = Modifier.padding(vertical = 12.dp))
        Text("الإعدادات", color = TextGray, fontSize = 12.sp)
        MenuItem(Icons.Default.Settings, "محركات لازينوفا")
        MenuItem(Icons.Default.Memory, "الذاكرة والخصوصية")
        MenuItem(Icons.Default.Palette, "المظهر")
        MenuItem(Icons.Default.VolumeUp, "الصوت واللغة")
        MenuItem(Icons.Default.Cloud, "الاتصال والخادم")
    }
}

@Composable
fun MenuItem(icon: androidx.compose.ui.graphics.vector.ImageVector, text: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { }
            .padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = TextGray, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(12.dp))
        Text(text, color = TextDark, fontSize = 16.sp)
    }
}

@Composable
fun TasksMenuContent() {
    Column(modifier = Modifier.padding(16.dp)) {
        Text("المهام والأدوات", fontWeight = FontWeight.Bold, fontSize = 18.sp, modifier = Modifier.fillMaxWidth(), textAlign = androidx.compose.ui.text.style.TextAlign.Center)
        Spacer(modifier = Modifier.height(16.dp))
        
        Text("المحادثة والملفات", color = TextGray, fontSize = 12.sp)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TaskButton(Icons.Default.AttachFile, "إضافة ملف")
            TaskButton(Icons.Default.PictureAsPdf, "إنشاء PDF")
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TaskButton(Icons.Default.FormatListBulleted, "تلخيص")
            TaskButton(Icons.Default.ManageSearch, "بحث عميق")
        }

        Spacer(modifier = Modifier.height(16.dp))
        Text("إدارة المهام والعمل", color = TextGray, fontSize = 12.sp)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TaskButton(Icons.Default.PlayArrow, "بدء التنفيذ")
            TaskButton(Icons.Default.CalendarMonth, "تخطيط المهام")
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TaskButton(Icons.Default.CloudUpload, "رفع الملفات")
            TaskButton(Icons.Default.Assignment, "إدارة المهام")
        }
    }
}

@Composable
fun RowScope.TaskButton(icon: androidx.compose.ui.graphics.vector.ImageVector, text: String) {
    Row(
        modifier = Modifier
            .weight(1f)
            .padding(4.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(BackgroundLight)
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = PurplePrimary, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(8.dp))
        Text(text, fontSize = 14.sp, color = TextDark)
    }
}
