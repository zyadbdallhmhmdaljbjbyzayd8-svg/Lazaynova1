package com.lazaynova.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ChatReply(val reply: String, val intent: String)

object ApiClient {
    private val allowedEngines = setOf(
        "chat",
        "research",
        "coding",
        "documents",
        "image",
        "video",
        "music",
        "agent"
    )

    suspend fun chat(
        message: String,
        history: List<Pair<String, String>>,
        engine: String = "chat"
    ): ChatReply = withContext(Dispatchers.IO) {
        require(engine in allowedEngines) {
            "المحرك المحدد غير معتمد"
        }

        val endpoint = BuildConfig.API_BASE_URL.trimEnd('/') +
            "/api/engines/$engine/run"

        val connection = URL(endpoint).openConnection() as HttpURLConnection

        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 15000
            connection.readTimeout = 120000
            connection.doOutput = true
            connection.setRequestProperty(
                "Content-Type",
                "application/json; charset=utf-8"
            )
            connection.setRequestProperty("Accept", "application/json")

            val historyJson = JSONArray()
            history.takeLast(10).forEach { (role, content) ->
                historyJson.put(
                    JSONObject()
                        .put("role", role)
                        .put("content", content)
                )
            }

            val payload = JSONObject()
                .put("message", message)
                .put("language", "ar")
                .put("history", historyJson)

            connection.outputStream.use {
                it.write(payload.toString().toByteArray(Charsets.UTF_8))
            }

            val status = connection.responseCode
            val stream = if (status in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }

            val body = stream?.bufferedReader(Charsets.UTF_8)?.use {
                it.readText()
            }.orEmpty()

            val json = try {
                JSONObject(body)
            } catch (_: Exception) {
                JSONObject()
            }

            if (status !in 200..299) {
                throw IllegalStateException(
                    json.optString(
                        "error",
                        "تعذر الاتصال بالخادم ($status)"
                    )
                )
            }

            ChatReply(
                reply = json.optString("reply", "لم يصل رد من الوكيل"),
                intent = json.optString("engine", engine)
            )
        } finally {
            connection.disconnect()
        }
    }
}
