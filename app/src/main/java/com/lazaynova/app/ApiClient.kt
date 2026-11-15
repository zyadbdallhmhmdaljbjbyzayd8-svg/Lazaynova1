package com.lazaynova.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ChatReply(
    val reply: String,
    val intent: String,
    val conversationId: String
)

object ApiClient {
    private val BASE = BuildConfig.API_BASE_URL.trimEnd('/').also {
        val endpoint = java.net.URI(it)
        require(endpoint.scheme == "http" && endpoint.host == "127.0.0.1") {
            "يجب أن يتصل التطبيق بالخادم المحلي فقط."
        }
    }

    private val allowedEngines = setOf(
        "chat", "research", "coding", "documents",
        "image", "video", "music", "agent"
    )

    @Volatile private var accessToken: String? = null
    @Volatile private var refreshToken: String? = null
    private val refreshMutex = Mutex()

    private fun request(
        path: String,
        method: String,
        body: JSONObject? = null,
        bearer: String? = null
    ): Pair<Int, JSONObject> {
        val connection =
            URL(BASE + path).openConnection() as HttpURLConnection

        try {
            connection.requestMethod = method
            connection.connectTimeout = 15000
            connection.readTimeout = 120000
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            if (!bearer.isNullOrBlank()) {
                connection.setRequestProperty(
                    "Authorization",
                    "Bearer $bearer"
                )
            }

            if (body != null) {
                connection.doOutput = true
                connection.outputStream.use {
                    it.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }

            val status = connection.responseCode
            val stream = if (status in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }

            val responseText = stream
                ?.bufferedReader(Charsets.UTF_8)
                ?.use { it.readText() }
                .orEmpty()

            val json = try {
                JSONObject(responseText)
            } catch (_: Exception) {
                JSONObject()
            }

            return status to json
        } finally {
            connection.disconnect()
        }
    }

    private fun errorMessage(
        status: Int,
        json: JSONObject
    ): String {
        return json.optString("error").takeIf { it.isNotBlank() }
            ?: "تعذر الاتصال بالخادم المركزي ($status)"
    }

    suspend fun authenticate(
        username: String,
        password: String,
        register: Boolean
    ): String = withContext(Dispatchers.IO) {
        require(username.matches(Regex("[A-Za-z0-9_.-]{3,32}"))) {
            "اسم المستخدم يجب أن يكون من 3 إلى 32 حرفاً إنجليزياً أو رقماً."
        }
        require(password.length >= 8) {
            "كلمة المرور يجب ألا تقل عن 8 أحرف."
        }

        val credentials = JSONObject()
            .put("username", username)
            .put("password", password)

        if (register) {
            val (registerStatus, registerJson) =
                request("/auth/register", "POST", credentials)

            if (registerStatus !in 200..299) {
                throw IllegalStateException(
                    errorMessage(registerStatus, registerJson)
                )
            }
        }

        val (status, json) =
            request("/auth/login", "POST", credentials)

        if (status !in 200..299) {
            throw IllegalStateException(errorMessage(status, json))
        }

        val newAccess = json.optString("access_token")
        val newRefresh = json.optString("refresh_token")

        require(newAccess.isNotBlank() && newRefresh.isNotBlank()) {
            "استجابة تسجيل الدخول لا تحتوي على الرموز المطلوبة."
        }

        accessToken = newAccess
        refreshToken = newRefresh

        "تم الاتصال بالخادم المركزي بنجاح."
    }

    private suspend fun refreshAccessToken(
        failedAccessToken: String
    ): Boolean = refreshMutex.withLock {
        if (accessToken != failedAccessToken) {
            return@withLock accessToken != null && refreshToken != null
        }

        val oldRefresh = refreshToken ?: return@withLock false

        try {
            val (status, json) = withContext(Dispatchers.IO) {
                request(
                    "/auth/refresh",
                    "POST",
                    JSONObject().put("refresh_token", oldRefresh)
                )
            }

            if (status !in 200..299) {
                accessToken = null
                refreshToken = null
                return@withLock false
            }

            val newAccess = json.optString("access_token")
            val newRefresh = json.optString("refresh_token")

            if (newAccess.isBlank() || newRefresh.isBlank()) {
                accessToken = null
                refreshToken = null
                return@withLock false
            }

            accessToken = newAccess
            refreshToken = newRefresh
            true
        } catch (_: Exception) {
            accessToken = null
            refreshToken = null
            false
        }
    }

    suspend fun chat(
        message: String,
        engine: String = "chat",
        conversationId: String? = null
    ): ChatReply = withContext(Dispatchers.IO) {
        require(engine in allowedEngines) {
            "المحرك المحدد غير معتمد."
        }
        require(message.isNotBlank()) {
            "اكتب رسالة أولاً."
        }

        var token = accessToken
            ?: throw IllegalStateException(
                "سجّل الدخول إلى الخادم المركزي أولاً."
            )

        val payload = JSONObject()
            .put("message", message)
            .put("engine", engine)

        if (!conversationId.isNullOrBlank()) {
            payload.put("conversation_id", conversationId)
        }

        var (status, json) =
            request("/v1/chat", "POST", payload, token)

        if (status == 401) {
            if (!refreshAccessToken(token)) {
                throw IllegalStateException(
                    "انتهت جلسة الدخول. سجّل الدخول مجدداً."
                )
            }

            token = accessToken
                ?: throw IllegalStateException(
                    "تعذر تجديد جلسة الدخول."
                )

            val retry = request("/v1/chat", "POST", payload, token)
            status = retry.first
            json = retry.second
        }

        if (status !in 200..299) {
            throw IllegalStateException(errorMessage(status, json))
        }

        val returnedConversationId =
            json.optString("conversation_id").trim()

        if (returnedConversationId.isBlank()) {
            throw IllegalStateException(
                "الخادم لم يُرجع معرّف المحادثة؛ لم يتم اعتماد الرد."
            )
        }

        val result = json.optJSONObject("result") ?: JSONObject()
        val output = result.opt("output")

        val text = when (output) {
            is String -> output
            is JSONObject -> output.optString("text", output.toString())
            else -> ""
        }.trim()

        val mode = result.optString("mode", "")

        val honestReply = when {
            text.isNotBlank() -> text
            mode == "model_unavailable" ->
                "الخادم المركزي متصل، لكن نموذج الاستدلال المحلي غير متاح حالياً."
            mode == "no_sources" ->
                "لم يعثر محرك البحث المحلي على مصادر كافية للإجابة."
            mode == "prompt_only" ->
                "هذا المحرك يجهّز وصفاً للمهمة فقط؛ لا توجد خدمة توليد وسائط متصلة حالياً."
            else ->
                "وصل الطلب إلى الخادم المركزي، لكن المحرك لم يُرجع نص إجابة. الحالة: ${mode.ifBlank { "غير محددة" }}"
        }

        ChatReply(
            reply = honestReply,
            intent = json.optString("engine", engine),
            conversationId = returnedConversationId
        )
    }


    private suspend fun authenticatedGet(path: String): JSONObject =
        withContext(Dispatchers.IO) {
            var token = accessToken
                ?: throw IllegalStateException("سجّل الدخول إلى الخادم المركزي أولاً.")

            var (status, json) = request(path, "GET", bearer = token)
            if (status == 401) {
                if (!refreshAccessToken(token)) {
                    throw IllegalStateException("انتهت جلسة الدخول. سجّل الدخول مجدداً.")
                }
                token = accessToken
                    ?: throw IllegalStateException("تعذر تجديد جلسة الدخول.")
                val retry = request(path, "GET", bearer = token)
                status = retry.first
                json = retry.second
            }

            if (status !in 200..299) {
                throw IllegalStateException(errorMessage(status, json))
            }
            json
        }

    suspend fun getConversationMessages(conversationId: String): List<ChatMessage> {
        require(conversationId.matches(Regex("[0-9a-f]{32}"))) {
            "معرّف المحادثة غير صالح."
        }
        val json = authenticatedGet("/v1/conversations/$conversationId")
        val rows = json.optJSONArray("messages") ?: return emptyList()
        return buildList {
            for (index in 0 until rows.length()) {
                val row = rows.optJSONObject(index) ?: continue
                val role = row.optString("role")
                if (role != "user" && role != "assistant") continue
                val content = row.optString("content")
                if (content.isBlank()) continue
                val seconds = row.optLong("ts", 0L)
                add(
                    ChatMessage(
                        id = index.toLong() + 1L,
                        role = role,
                        text = content,
                        timestamp = if (seconds > 0L) seconds * 1000L
                                    else System.currentTimeMillis()
                    )
                )
            }
        }
    }

    fun clearSession() {
        accessToken = null
        refreshToken = null
    }
}
