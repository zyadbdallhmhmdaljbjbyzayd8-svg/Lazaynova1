package com.lazaynova.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.lazaynova.app.ui.LazaynovaScreen
import com.lazaynova.app.ui.theme.LazaynovaTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            LazaynovaTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    LazaynovaScreen()
                }
            }
        }
    }
}
