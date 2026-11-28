package com.lazaynova.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class CloudConversation(
    val id: String,
    val title: String,
    val engineId: String,
    val createdAt: String = "",
    val updatedAt: String = ""
)

data class CloudMessage(
    val id: String,
    val role: String,
    val content: String,
    val engineId: String = "",
    val createdAt: String = ""
)

data class ChatSendResult(
    val answer: String,
    val conversationId: String
)

class ChatRepository {

    private val baseUrl: String
        get() = BuildConfig.API_BASE_URL.trimEnd('/')

    private fun execute(
        path: String,
        method: String,
        payload: JSONObject?,
        token: String?
    ): Pair<Int, JSONObject> {
        val connection = URL(baseUrl + path)
            .openConnection() as HttpURLConnection

        try {
            connection.requestMethod = method
            connection.connectTimeout = 15000
            connection.readTimeout = 120000
            connection.setRequestProperty("Accept", "application/json")

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

            if (!token.isNullOrBlank()) {
                connection.setRequestProperty(
                    "Authorization",
                    "Bearer $token"
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

            return status to json
        } finally {
            connection.disconnect()
        }
    }

    private suspend fun request(
        path: String,
        method: String = "GET",
        payload: JSONObject? = null,
        authenticated: Boolean = true
    ): JSONObject = withContext(Dispatchers.IO) {
        var token = if (authenticated) {
            AuthSessionManager.getAccessToken()
                ?: throw IllegalStateException(
                    "يلزم تسجيل الدخول للوصول إلى بياناتك."
                )
        } else null

        var (status, json) = execute(path, method, payload, token)

        if (status == 401 && authenticated) {
            token = AuthSessionManager.refreshAfterUnauthorized()
                ?: throw IllegalStateException(
                    "انتهت جلسة الدخول. سجّل الدخول مجددًا."
                )

            val retry = execute(path, method, payload, token)
            status = retry.first
            json = retry.second
        }

        if (status !in 200..299) {
            val message = json.optString(
                "error",
                "فشل الاتصال بالخادم (HTTP $status)"
            )
            throw IllegalStateException(message)
        }

        json
    }

    suspend fun sendMessage(
        message: String,
        engineId: String,
        conversationId: String? = null
    ): ChatSendResult {
        val payload = JSONObject()
            .put("message", message)
            .put("engineId", engineId)
            .put("useOrchestrator", engineId == "agent")

        if (!conversationId.isNullOrBlank()) {
            payload.put("conversationId", conversationId)
        }

        val result = request(
            path = "/api/chat",
            method = "POST",
            payload = payload
        )

        val answer = result.optString("response")
            .ifBlank { "وصل رد فارغ من خادم Lazaynova." }

        val returnedId = result.optString("conversationId")
            .ifBlank {
                conversationId ?: throw IllegalStateException(
                    "لم يُرجع الخادم معرّف المحادثة."
                )
            }

        return ChatSendResult(answer, returnedId)
    }

    suspend fun listConversations(): List<CloudConversation> {
        val array = request("/api/conversations")
            .optJSONArray("conversations") ?: return emptyList()

        return buildList {
            for (i in 0 until array.length()) {
                val item = array.optJSONObject(i) ?: continue
                add(
                    CloudConversation(
                        id = item.optString("id"),
                        title = item.optString("title", "محادثة"),
                        engineId = item.optString("engine_id", "chat"),
                        createdAt = item.optString("created_at"),
                        updatedAt = item.optString("updated_at")
                    )
                )
            }
        }
    }

    suspend fun createConversation(
        title: String,
        engineId: String
    ): CloudConversation {
        val result = request(
            path = "/api/conversations",
            method = "POST",
            payload = JSONObject()
                .put("title", title)
                .put("engineId", engineId)
        )

        val item = result.optJSONObject("conversation")
            ?: throw IllegalStateException("استجابة إنشاء المحادثة غير صالحة.")

        return CloudConversation(
            id = item.getString("id"),
            title = item.optString("title", title),
            engineId = item.optString("engine_id", engineId),
            createdAt = item.optString("created_at"),
            updatedAt = item.optString("updated_at")
        )
    }

    suspend fun loadMessages(conversationId: String): List<CloudMessage> {
        val result = request(
            "/api/conversations/$conversationId/messages"
        )
        val array = result.optJSONArray("messages") ?: return emptyList()

        return buildList {
            for (i in 0 until array.length()) {
                val item = array.optJSONObject(i) ?: continue
                add(
                    CloudMessage(
                        id = item.optString("id"),
                        role = item.optString("role"),
                        content = item.optString("content"),
                        engineId = item.optString("engine_id"),
                        createdAt = item.optString("created_at")
                    )
                )
            }
        }
    }

    suspend fun archiveConversation(conversationId: String) {
        request(
            path = "/api/conversations/$conversationId",
            method = "DELETE"
        )
    }

    suspend fun getPreferences(): JSONObject {
        return request("/api/preferences")
            .optJSONObject("preferences") ?: JSONObject()
    }

    suspend fun savePreferences(preferences: JSONObject): JSONObject {
        return request(
            path = "/api/preferences",
            method = "PUT",
            payload = preferences
        ).optJSONObject("preferences") ?: JSONObject()
    }
}
