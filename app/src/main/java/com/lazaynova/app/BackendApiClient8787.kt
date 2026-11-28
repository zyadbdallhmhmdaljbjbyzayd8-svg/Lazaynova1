package com.lazaynova.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

data class ApiCallResult(
    val ok: Boolean,
    val statusCode: Int,
    val rawBody: String,
    val errorMessage: String? = null
)

class BackendApiClient8787(
    private val config: BackendRuntimeConfig = BackendRuntimeConfig()
) {
    private fun normalizedBase(): String = config.baseUrl.trim().trimEnd('/')

    private suspend fun requestJson(
        method: String,
        path: String,
        bearerToken: String? = null,
        jsonBody: JSONObject? = null
    ): ApiCallResult = withContext(Dispatchers.IO) {
        var conn: HttpURLConnection? = null
        try {
            val targetUrl = URL("${normalizedBase()}$path")
            conn = (targetUrl.openConnection() as HttpURLConnection).apply {
                requestMethod = method
                connectTimeout = (config.requestTimeoutSec * 1000L).toInt().coerceAtLeast(5000)
                readTimeout = (config.requestTimeoutSec * 1000L).toInt().coerceAtLeast(5000)
                useCaches = false
                setRequestProperty("Accept", "application/json")
                if (!bearerToken.isNullOrBlank()) {
                    setRequestProperty("Authorization", "Bearer $bearerToken")
                }
                if (jsonBody != null) {
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    OutputStreamWriter(outputStream, Charsets.UTF_8).use { writer ->
                        writer.write(jsonBody.toString())
                        writer.flush()
                    }
                }
            }

            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val bodyText = if (stream != null) {
                BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).use { it.readText() }
            } else {
                ""
            }

            if (code in 200..299) {
                ApiCallResult(ok = true, statusCode = code, rawBody = bodyText)
            } else {
                val parsedErr = try {
                    val obj = JSONObject(bodyText)
                    obj.optString("error").ifBlank {
                        obj.optJSONObject("error")?.optString("message") ?: bodyText
                    }
                } catch (_: Exception) {
                    bodyText
                }
                ApiCallResult(
                    ok = false,
                    statusCode = code,
                    rawBody = bodyText,
                    errorMessage = parsedErr.ifBlank { "HTTP $code from port 8787" }
                )
            }
        } catch (e: Exception) {
            ApiCallResult(
                ok = false,
                statusCode = -1,
                rawBody = "",
                errorMessage = e.message ?: e.javaClass.simpleName
            )
        } finally {
            conn?.disconnect()
        }
    }

    suspend fun checkHealth(): ApiCallResult = requestJson("GET", "/health")

    suspend fun listEngines(token: String? = null): ApiCallResult =
        requestJson("GET", "/api/engines", bearerToken = token)

    suspend fun listConversations(token: String?): ApiCallResult =
        requestJson("GET", "/api/conversations", bearerToken = token)

    suspend fun createConversation(token: String?, engineId: String, title: String? = null): ApiCallResult {
        val body = JSONObject().apply {
            put("engineId", engineId)
            if (!title.isNullOrBlank()) put("title", title)
        }
        return requestJson("POST", "/api/conversations", bearerToken = token, jsonBody = body)
    }

    suspend fun getMessages(token: String?, conversationId: String): ApiCallResult =
        requestJson("GET", "/api/conversations/$conversationId/messages", bearerToken = token)

    suspend fun sendChat(
        token: String?,
        message: String,
        engineId: String,
        conversationId: String? = null
    ): ApiCallResult {
        val body = JSONObject().apply {
            put("message", message)
            put("engineId", engineId)
            if (!conversationId.isNullOrBlank()) put("conversationId", conversationId)
        }
        return requestJson("POST", "/api/chat", bearerToken = token, jsonBody = body)
    }

    companion object {
        fun parseConversations(rawJson: String): List<ConversationSummary> {
            return try {
                val arr: JSONArray = when {
                    rawJson.trim().startsWith("[") -> JSONArray(rawJson)
                    else -> {
                        val root = JSONObject(rawJson)
                        root.optJSONArray("conversations") ?: root.optJSONArray("data") ?: JSONArray()
                    }
                }
                buildList {
                    for (i in 0 until arr.length()) {
                        val item = arr.optJSONObject(i) ?: continue
                        val id = item.optString("id")
                        if (id.isNotBlank()) {
                            add(
                                ConversationSummary(
                                    id = id,
                                    title = item.optString("title", "محادثة"),
                                    engineId = item.optString("engineId", "chat")
                                )
                            )
                        }
                    }
                }
            } catch (_: Exception) {
                emptyList()
            }
        }

        fun parseMessages(rawJson: String): List<ChatMessageItem> {
            return try {
                val arr: JSONArray = when {
                    rawJson.trim().startsWith("[") -> JSONArray(rawJson)
                    else -> {
                        val root = JSONObject(rawJson)
                        root.optJSONArray("messages") ?: root.optJSONArray("data") ?: JSONArray()
                    }
                }
                buildList {
                    for (i in 0 until arr.length()) {
                        val item = arr.optJSONObject(i) ?: continue
                        val id = item.optString("id", "msg_$i")
                        val role = item.optString("role", "assistant")
                        val content = item.optString("content", "")
                        if (content.isNotBlank()) {
                            add(
                                ChatMessageItem(
                                    id = id,
                                    role = role,
                                    content = content,
                                    engineName = item.optString("engine", "").takeIf { it.isNotBlank() }
                                )
                            )
                        }
                    }
                }
            } catch (_: Exception) {
                emptyList()
            }
        }
    }
}
