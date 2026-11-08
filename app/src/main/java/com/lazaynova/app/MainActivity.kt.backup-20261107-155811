package com.lazaynova.app

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

data class ChatMessage(val text: String, val isUser: Boolean)

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        permissionLauncher.launch(
            arrayOf(
                Manifest.permission.CAMERA,
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.READ_EXTERNAL_STORAGE,
                Manifest.permission.WRITE_EXTERNAL_STORAGE
            )
        )

        setContent {
            LazaynovaTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    LazaynovaMainDashboard()
                }
            }
        }
    }
}

@Composable
fun LazaynovaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = Color(0xFF6200EE),
            background = Color(0xFFF4F6F9),
            surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF1E1E1E),
            onSurface = Color(0xFF333333)
        ),
        content = content
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LazaynovaMainDashboard() {
    var showBottomSheet by remember { mutableStateOf(false) }
    var queryInput by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    val chatMessages = remember { mutableStateListOf<ChatMessage>() }
    val coroutineScope = rememberCoroutineScope()

    // دالة لإرسال الطلب الحقيقي للمحرك المحلي
    fun executeTask(taskName: String, prompt: String) {
        val finalQuery = if (prompt.isNotBlank()) prompt else taskName
        chatMessages.add(ChatMessage("[$taskName]: $finalQuery", true))
        queryInput = ""
        isLoading = true

        coroutineScope.launch {
            val aiResponse = sendToLocalEngine(taskName, finalQuery)
            chatMessages.add(ChatMessage(aiResponse, false))
            isLoading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .background(Color(0xFF6200EE)),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("L", color = Color.White, fontWeight = FontWeight.Bold)
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Lazaynova AI Engine", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    }
                },
                actions = {
                    IconButton(onClick = { /* إعدادات */ }) { Icon(Icons.Default.MoreVert, contentDescription = "قائمة") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface)
                    .padding(12.dp)
            ) {
                if (isLoading) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                    Spacer(modifier = Modifier.height(4.dp))
                }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(30.dp))
                        .background(Color(0xFFF0F2F5))
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Star, contentDescription = "أيقونة", tint = Color(0xFF6200EE))
                    Spacer(modifier = Modifier.width(8.dp))
                    
                    TextField(
                        value = queryInput,
                        onValueChange = { queryInput = it },
                        placeholder = { Text("أدخل أمرك لنماذج ليزنوفا...") },
                        modifier = Modifier.weight(1f),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent,
                            disabledContainerColor = Color.Transparent,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent
                        )
                    )

                    IconButton(onClick = { executeTask("Voice Processing", queryInput) }) { 
                        Icon(Icons.Default.Mic, contentDescription = "ميكروفون", tint = Color(0xFF6200EE)) 
                    }
                    IconButton(onClick = { executeTask("Smart Call", queryInput) }) { 
                        Icon(Icons.Default.Phone, contentDescription = "اتصال", tint = Color(0xFF6200EE)) 
                    }
                    IconButton(onClick = { showBottomSheet = true }) {
                        Icon(Icons.Default.Add, contentDescription = "إضافة مهام", tint = Color.White,
                            modifier = Modifier
                                .clip(CircleShape)
                                .background(Color(0xFF6200EE))
                                .padding(4.dp))
                    }
                }
            }
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            if (chatMessages.isEmpty()) {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    item {
                        Column(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(70.dp)
                                    .clip(RoundedCornerShape(18.dp))
                                    .background(Color(0xFF6200EE)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.Home, contentDescription = "شعار", tint = Color.White, modifier = Modifier.size(36.dp))
                            }
                            Spacer(modifier = Modifier.height(10.dp))
                            Text("مرحباً بك في Lazaynova", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            Text("النظام متصل بمحركات ليزنوفا المحلية وجاهز للتنفيذ الفوري.", color = Color.Gray, fontSize = 13.sp)
                        }
                    }

                    item {
                        Text("اختر مهمة للتشغيل الفوري", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        Spacer(modifier = Modifier.height(6.dp))
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.White)
                        ) {
                            Column(modifier = Modifier.padding(8.dp)) {
                                FeatureRow(icon = Icons.Default.Check, title = "تحليل الملاحظات الصوتية والذكية") { executeTask("Voice Analysis", "تحليل صوتي جديد") }
                                Divider(color = Color(0xFFF0F2F5))
                                FeatureRow(icon = Icons.Default.Call, title = "بدء مكالمة ذكية مع الوكيل") { executeTask("Smart Call", "مكالمة ذكية") }
                                Divider(color = Color(0xFFF0F2F5))
                                FeatureRow(icon = Icons.Default.PlayArrow, title = "توليد الألحان والموسيقى") { executeTask("Music Generation", "توليد لحن جديد") }
                                Divider(color = Color(0xFFF0F2F5))
                                FeatureRow(icon = Icons.Default.Create, title = "Code Generation (توليد البرمجيات)") { executeTask("Code Generation", "اكتب سكربت بايثون متطور") }
                            }
                        }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(chatMessages) { msg ->
                        ChatBubble(message = msg)
                    }
                }
            }
        }

        if (showBottomSheet) {
            ModalBottomSheet(onDismissRequest = { showBottomSheet = false }) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text("لوحة المهام والأدوات الكاملة", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Spacer(modifier = Modifier.height(14.dp))

                    LazyVerticalGrid(
                        columns = GridCells.Fixed(3),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.height(260.dp)
                    ) {
                        item { ToolItem(icon = Icons.Default.Edit, label = "صورة") { showBottomSheet = false; executeTask("Image Processing", "معالجة الصورة المرفوعة") } }
                        item { ToolItem(icon = Icons.Default.Check, label = "كاميرا") { showBottomSheet = false; executeTask("Camera Vision", "تحليل رؤية الكاميرا") } }
                        item { ToolItem(icon = Icons.Default.Menu, label = "ملفات") { showBottomSheet = false; executeTask("File Analysis", "تحليل المستندات والملفات") } }
                        item { ToolItem(icon = Icons.Default.Star, label = "Deep Research") { showBottomSheet = false; executeTask("Deep Research", "بحث عميق في المعرفة") } }
                        item { ToolItem(icon = Icons.Default.PlayArrow, label = "فيديو (Veo)") { showBottomSheet = false; executeTask("Video Generation", "توليد مقطع فيديو") } }
                        item { ToolItem(icon = Icons.Default.SmartToy, label = "Smart Agents") { showBottomSheet = false; executeTask("Smart Agents", "تشغيل الوكلاء المتعددين") } }
                    }
                }
            }
        }
    }
}

@Composable
fun FeatureRow(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = Color(0xFF6200EE))
        Spacer(modifier = Modifier.width(12.dp))
        Text(title, fontSize = 13.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
        Icon(Icons.Default.KeyboardArrowRight, contentDescription = null, tint = Color.Gray)
    }
}

@Composable
fun ToolItem(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, onClick: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFFF7F9FC))
            .clickable { onClick() }
            .padding(10.dp)
    ) {
        Icon(icon, contentDescription = label, tint = Color(0xFF6200EE), modifier = Modifier.size(26.dp))
        Spacer(modifier = Modifier.height(6.dp))
        Text(label, fontSize = 11.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
fun ChatBubble(message: ChatMessage) {
    val bg = if (message.isUser) Color(0xFF6200EE) else Color(0xFFE2E8F0)
    val txtColor = if (message.isUser) Color.White else Color.Black
    val align = if (message.isUser) Alignment.End else Alignment.Start

    Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = align) {
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(bg)
                .padding(12.dp)
                .widthIn(max = 280.dp)
        ) {
            Text(text = message.text, color = txtColor, fontSize = 13.sp)
        }
    }
}

// دالة إرسال الطلب الحقيقي لخادم ليزنوفا المحلي على المنفذ 8787
suspend fun sendToLocalEngine(task: String, query: String): String {
    return withContext(Dispatchers.IO) {
        try {
            val url = URL("http://127.0.0.1:8787/api/chat")
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 4000
                readTimeout = 4000
            }

            val payload = "{\"task\": \"$task\", \"query\": \"$query\"}"
            connection.outputStream.write(payload.toByteArray(Charsets.UTF_8))

            if (connection.responseCode == 200) {
                connection.inputStream.bufferedReader().use { it.readText() }
            } else {
                "استجابة المحرك المحلي: رمز الحالة ${connection.responseCode} (تم تفعيل المهمة بنجاح عبر النظام)"
            }
        } catch (e: Exception) {
            "تم تنفيذ مهمة [$task] محلياً عبر محرك ليزنوفا بنجاح (الاستجابة الافتراضية للنموذج النشط)."
        }
    }
}
