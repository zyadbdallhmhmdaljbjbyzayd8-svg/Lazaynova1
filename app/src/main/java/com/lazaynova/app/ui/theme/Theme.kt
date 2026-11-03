package com.lazaynova.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val PurplePrimary = Color(0xFF7B3FF2)
val PurpleLight = Color(0xFFEDE7FF)
val BackgroundLight = Color(0xFFF8F9FA)
val SurfaceWhite = Color(0xFFFFFFFF)
val TextDark = Color(0xFF1E1E1E)
val TextGray = Color(0xFF888888)

private val LightColors = lightColorScheme(
    primary = PurplePrimary,
    onPrimary = Color.White,
    secondary = PurpleLight,
    onSecondary = PurplePrimary,
    background = BackgroundLight,
    surface = SurfaceWhite,
    onBackground = TextDark,
    onSurface = TextDark
)

@Composable
fun LazaynovaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content
    )
}
