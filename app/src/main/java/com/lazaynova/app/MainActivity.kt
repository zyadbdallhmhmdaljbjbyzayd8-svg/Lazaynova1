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

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        // تفعيل الأذونات تلقائياً للميكروفون، الكاميرا، والتخزين لخدمة مئات الآلاف من المستخدمين بكفاءة
    }

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
                        Text("Lazaynova", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    }
                },
                actions = {
                    IconButton(onClick = { /* إعدادات */ }) { Icon(Icons.Default.MoreVert, contentDescription = "قائمة") }
                    IconButton(onClick = { /* القائمة الجانبية */ }) { Icon(Icons.Default.Menu, contentDescription = "القائمة الرئيسية") }
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
                        placeholder = { Text("أدخل سؤالك أو تخيلك...") },
                        modifier = Modifier.weight(1f),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent,
                            disabledContainerColor = Color.Transparent,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent
                        )
                    )

                    IconButton(onClick = { /* تفعيل الصوت */ }) { Icon(Icons.Default.Mic, contentDescription = "ميكروفون", tint = Color.Gray) }
                    IconButton(onClick = { /* تفعيل الاتصال */ }) { Icon(Icons.Default.Phone, contentDescription = "اتصال", tint = Color.Gray) }
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
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
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
                    Text("أنا مساعدك الذكي، جاهز لمساعدتك في أي شيء تخيله أو تحتاجه.", color = Color.Gray, fontSize = 13.sp)
                }
            }

            item {
                Text("المميزات والمهام الرئيسية", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Spacer(modifier = Modifier.height(6.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(modifier = Modifier.padding(8.dp)) {
                        FeatureRow(icon = Icons.Default.Check, title = "تسجيل وتحليل الملاحظات الصوتية")
                        Divider(color = Color(0xFFF0F2F5))
                        FeatureRow(icon = Icons.Default.Call, title = "مكالمات صوتية ومرئية ذكية")
                        Divider(color = Color(0xFFF0F2F5))
                        FeatureRow(icon = Icons.Default.PlayArrow, title = "توليد الموسيقى والألحان الذكية")
                        Divider(color = Color(0xFFF0F2F5))
                        FeatureRow(icon = Icons.Default.Create, title = "Code Generation & Development")
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
                        item { ToolItem(icon = Icons.Default.Edit, label = "صورة") }
                        item { ToolItem(icon = Icons.Default.Check, label = "كاميرا") }
                        item { ToolItem(icon = Icons.Default.Menu, label = "ملفات") }
                        item { ToolItem(icon = Icons.Default.Star, label = "إنشاء صور") }
                        item { ToolItem(icon = Icons.Default.PlayArrow, label = "فيديو (Veo)") }
                        item { ToolItem(icon = Icons.Default.Call, label = "مكالمة ذكية") }
                    }
                }
            }
        }
    }
}

@Composable
fun FeatureRow(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { }
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
fun ToolItem(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFFF7F9FC))
            .clickable { }
            .padding(10.dp)
    ) {
        Icon(icon, contentDescription = label, tint = Color(0xFF6200EE), modifier = Modifier.size(26.dp))
        Spacer(modifier = Modifier.height(6.dp))
        Text(label, fontSize = 11.sp, fontWeight = FontWeight.Medium)
    }
}
