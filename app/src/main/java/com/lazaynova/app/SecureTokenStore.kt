package com.lazaynova.app

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SecureTokenStore(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("lazaynova_secure_session_prefs", Context.MODE_PRIVATE)

    private fun getOrCreateSecretKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = keyStore.getEntry(KEY_ALIAS, null) as? KeyStore.SecretKeyEntry
        if (existing != null) {
            return existing.secretKey
        }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        generator.init(spec)
        return generator.generateKey()
    }

    private fun encryptValue(plain: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateSecretKey())
        val iv = cipher.iv
        val encrypted = cipher.doFinal(plain.toByteArray(StandardCharsets.UTF_8))
        val ivB64 = Base64.encodeToString(iv, Base64.NO_WRAP)
        val ctB64 = Base64.encodeToString(encrypted, Base64.NO_WRAP)
        return "$ivB64:$ctB64"
    }

    private fun decryptValue(encoded: String): String? {
        return try {
            val parts = encoded.split(":", limit = 2)
            if (parts.size != 2) return null
            val iv = Base64.decode(parts[0], Base64.NO_WRAP)
            val ct = Base64.decode(parts[1], Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateSecretKey(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(ct), StandardCharsets.UTF_8)
        } catch (_: Exception) {
            null
        }
    }

    fun saveSession(
        accessToken: String,
        provider: String = "google",
        accountEmail: String? = null,
        expiresAtEpochMs: Long = 0L
    ) {
        prefs.edit()
            .putString(KEY_ACCESS_TOKEN, encryptValue(accessToken))
            .putString(KEY_PROVIDER, provider)
            .putString(KEY_EMAIL, accountEmail ?: "")
            .putLong(KEY_EXPIRES_AT, expiresAtEpochMs)
            .apply()
    }

    fun getAccessToken(): String? {
        val raw = prefs.getString(KEY_ACCESS_TOKEN, null)?.takeIf { it.isNotBlank() } ?: return null
        return decryptValue(raw)?.takeIf { it.isNotBlank() }
    }

    fun getProvider(): String =
        prefs.getString(KEY_PROVIDER, "google") ?: "google"

    fun getAccountEmail(): String? =
        prefs.getString(KEY_EMAIL, null)?.takeIf { it.isNotBlank() }

    fun getExpiresAtEpochMs(): Long =
        prefs.getLong(KEY_EXPIRES_AT, 0L)

    fun isExpired(nowEpochMs: Long = System.currentTimeMillis()): Boolean {
        val exp = getExpiresAtEpochMs()
        return exp > 0L && nowEpochMs >= exp
    }

    fun clearSession() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_ALIAS = "lazaynova_session_aes_key"
        private const val KEY_ACCESS_TOKEN = "lz_session_token_enc"
        private const val KEY_PROVIDER = "lz_auth_provider"
        private const val KEY_EMAIL = "lz_account_email"
        private const val KEY_EXPIRES_AT = "lz_session_expires_at"
    }
}
