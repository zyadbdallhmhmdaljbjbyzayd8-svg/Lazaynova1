package com.lazaynova.app

import android.content.Context
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

enum class LazaynovaThemeMode(val storageValue: String) {
    SYSTEM("system"),
    LIGHT("light"),
    DARK("dark");

    companion object {
        fun from(value: String?): LazaynovaThemeMode =
            entries.firstOrNull { it.storageValue == value } ?: SYSTEM
    }
}

private val LightColors = lightColorScheme(
    primary = Color(0xFF6841D9),
    secondary = Color(0xFF2878D0),
    background = Color(0xFFF5F7FC),
    surface = Color(0xFFFFFFFF),
    onBackground = Color(0xFF151B2D),
    onSurface = Color(0xFF151B2D),
    surfaceVariant = Color(0xFFEEF0FF),
    onSurfaceVariant = Color(0xFF68738A),
    outlineVariant = Color(0xFFE1E6F0)
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFB6A0FF),
    secondary = Color(0xFF75B8FF),
    background = Color(0xFF070A14),
    surface = Color(0xFF10182A),
    onBackground = Color(0xFFEAF0FF),
    onSurface = Color(0xFFEAF0FF),
    surfaceVariant = Color(0xFF20213D),
    onSurfaceVariant = Color(0xFFADB8D0),
    outlineVariant = Color(0xFF263149)
)

@Composable
fun LazaynovaTheme(
    content: @Composable (
        LazaynovaThemeMode,
        (LazaynovaThemeMode) -> Unit
    ) -> Unit
) {
    val context = LocalContext.current

    val preferences = remember(context) {
        context.getSharedPreferences(
            "lazaynova_preferences",
            Context.MODE_PRIVATE
        )
    }

    var mode by remember {
        mutableStateOf(
            LazaynovaThemeMode.from(
                preferences.getString("theme_mode", "system")
            )
        )
    }

    val systemDark = isSystemInDarkTheme()

    val dark = when (mode) {
        LazaynovaThemeMode.SYSTEM -> systemDark
        LazaynovaThemeMode.LIGHT -> false
        LazaynovaThemeMode.DARK -> true
    }

    MaterialTheme(
        colorScheme = if (dark) DarkColors else LightColors
    ) {
        content(mode) { selected ->
            mode = selected
            preferences.edit()
                .putString("theme_mode", selected.storageValue)
                .apply()
        }
    }
}
