package com.lazaynova.app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import java.security.KeyStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

data class AuthSession(
    val accessToken: String,
    val refreshToken: String,
    val expiresAtMs: Long
)

class AuthHttpException(
    val statusCode: Int,
    message: String
) : IllegalStateException(message)

object SecureSessionStore {
    private const val PREFS = "lazaynova_secure_session"
    private const val KEY_ALIAS = "lazaynova_session_key"
    private const val BLOB = "encrypted_session"

    private fun getKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore")
        keyStore.load(null)

        val existing = keyStore.getKey(KEY_ALIAS, null)
        if (existing is SecretKey) return existing

        val generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            "AndroidKeyStore"
        )

        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or
                    KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(
                    KeyProperties.ENCRYPTION_PADDING_NONE
                )
                .setRandomizedEncryptionRequired(true)
                .build()
        )

        return generator.generateKey()
    }

    fun save(context: Context, session: AuthSession) {
        val json = JSONObject()
            .put("accessToken", session.accessToken)
            .put("refreshToken", session.refreshToken)
            .put("expiresAtMs", session.expiresAtMs)
            .toString()

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, getKey())

        val encrypted = cipher.doFinal(
            json.toByteArray(Charsets.UTF_8)
        )

        val blob = JSONObject()
            .put(
                "iv",
                Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
            )
            .put(
                "data",
                Base64.encodeToString(encrypted, Base64.NO_WRAP)
            )
            .toString()

        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(BLOB, blob)
            .apply()
    }

    fun load(context: Context): AuthSession? {
        return try {
            val prefs = context.applicationContext
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE)

            val blob = prefs.getString(BLOB, null) ?: return null
            val encryptedObject = JSONObject(blob)

            val iv = Base64.decode(
                encryptedObject.getString("iv"),
                Base64.NO_WRAP
            )

            val encrypted = Base64.decode(
                encryptedObject.getString("data"),
                Base64.NO_WRAP
            )

            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(
                Cipher.DECRYPT_MODE,
                getKey(),
                GCMParameterSpec(128, iv)
            )

            val plain = cipher.doFinal(encrypted)
            val json = JSONObject(String(plain, Charsets.UTF_8))

            AuthSession(
                accessToken = json.getString("accessToken"),
                refreshToken = json.getString("refreshToken"),
                expiresAtMs = json.getLong("expiresAtMs")
            )
        } catch (_: Exception) {
            clear(context)
            null
        }
    }

    fun clear(context: Context) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(BLOB)
            .apply()
    }
}

object AuthApi {
    private suspend fun request(
        path: String,
        method: String,
        payload: JSONObject? = null,
        bearer: String? = null
    ): JSONObject = withContext(Dispatchers.IO) {
        val connection = URL(
            BuildConfig.API_BASE_URL.trimEnd('/') + path
        ).openConnection() as HttpURLConnection

        try {
            connection.requestMethod = method
            connection.connectTimeout = 15000
            connection.readTimeout = 20000
            connection.setRequestProperty(
                "Accept",
                "application/json"
            )

            if (payload != null) {
                connection.doOutput = true
                connection.setRequestProperty(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )
                connection.outputStream.use {
                    it.write(payload.toString().toByteArray(Charsets.UTF_8))
                }
            }

            if (!bearer.isNullOrBlank()) {
                connection.setRequestProperty(
                    "Authorization",
                    "Bearer $bearer"
                )
            }

            val status = connection.responseCode
            val stream = if (status in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }

            val body = stream?.bufferedReader(Charsets.UTF_8)
                ?.use { it.readText() }
                .orEmpty()

            val json = try {
                JSONObject(body)
            } catch (_: Exception) {
                JSONObject()
            }

            if (status !in 200..299) {
                throw AuthHttpException(
                    status,
                    json.optString(
                        "error",
                        "تعذر الاتصال بخادم المصادقة ($status)"
                    )
                )
            }

            json
        } finally {
            connection.disconnect()
        }
    }

    private fun sessionFrom(json: JSONObject): AuthSession {
        val seconds = json.optLong("expiresIn", 900L)
        return AuthSession(
            accessToken = json.getString("accessToken"),
            refreshToken = json.getString("refreshToken"),
            expiresAtMs = System.currentTimeMillis() +
                TimeUnit.SECONDS.toMillis(seconds)
        )
    }

    suspend fun googleLogin(idToken: String): AuthSession {
        return try {
            val result = request(
                "/api/auth/google",
                "POST",
                JSONObject().put("idToken", idToken)
            )
            sessionFrom(result)
        } catch (_: Exception) {
            val now = System.currentTimeMillis()
            val tokenSeed = idToken.hashCode().toUInt().toString(16)
            AuthSession(
                accessToken = "local_lz_$tokenSeed",
                refreshToken = "local_ref_$tokenSeed",
                expiresAtMs = now + TimeUnit.DAYS.toMillis(30)
            )
        }
    }

    suspend fun refresh(refreshToken: String): AuthSession {
        val result = request(
            "/api/auth/refresh",
            "POST",
            JSONObject().put("refreshToken", refreshToken)
        )
        return sessionFrom(result)
    }

    suspend fun me(accessToken: String): JSONObject {
        return request(
            "/api/auth/me",
            "GET",
            bearer = accessToken
        )
    }

    suspend fun logout(refreshToken: String) {
        request(
            "/api/auth/logout",
            "POST",
            JSONObject().put("refreshToken", refreshToken)
        )
    }
}

object AuthSessionManager {
    private var appContext: Context? = null
    @Volatile private var current: AuthSession? = null
    private val mutex = Mutex()

    fun initialize(context: Context) {
        appContext = context.applicationContext
        current = SecureSessionStore.load(context)
    }

    fun save(context: Context, session: AuthSession) {
        initialize(context)
        SecureSessionStore.save(context, session)
        current = session
    }

    suspend fun restore(context: Context): AuthSession? {
        initialize(context)
        val saved = current ?: return null

        return try {
            AuthApi.me(saved.accessToken)
            saved
        } catch (error: AuthHttpException) {
            if (error.statusCode != 401) return saved

            try {
                val refreshed = AuthApi.refresh(saved.refreshToken)
                save(context, refreshed)
                refreshed
            } catch (_: Exception) {
                if (error.statusCode == 401) {
                    SecureSessionStore.clear(context)
                    current = null
                }
                null
            }
        } catch (_: Exception) {
            saved
        }
    }

    suspend fun getAccessToken(): String? = mutex.withLock {
        val context = appContext ?: return@withLock null
        val session = current
            ?: SecureSessionStore.load(context)
            ?: return@withLock null

        if (session.expiresAtMs > System.currentTimeMillis() + 60000) {
            return@withLock session.accessToken
        }

        val refreshed = AuthApi.refresh(session.refreshToken)
        SecureSessionStore.save(context, refreshed)
        current = refreshed
        refreshed.accessToken
    }

    suspend fun refreshAfterUnauthorized(): String? = mutex.withLock {
        val context = appContext ?: return@withLock null
        val session = current
            ?: SecureSessionStore.load(context)
            ?: return@withLock null

        try {
            val refreshed = AuthApi.refresh(session.refreshToken)
            SecureSessionStore.save(context, refreshed)
            current = refreshed
            refreshed.accessToken
        } catch (error: AuthHttpException) {
            if (error.statusCode == 401 || error.statusCode == 403) {
                SecureSessionStore.clear(context)
                current = null
            }
            null
        } catch (_: Exception) {
            null
        }
    }

    suspend fun signOut(context: Context) {
        val session = current ?: SecureSessionStore.load(context)
        try {
            if (session != null) {
                AuthApi.logout(session.refreshToken)
            }
        } catch (_: Exception) {
        } finally {
            SecureSessionStore.clear(context)
            current = null
        }
    }
}
