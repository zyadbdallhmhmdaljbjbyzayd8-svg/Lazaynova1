package com.lazaynova.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class ChatRepository {

    companion object {
        private const val CHAT_URL =
            "http://127.0.0.1:8787/api/chat"
    }

    suspend fun sendMessage(
        message: String,
        engineId: String
    ): String = withContext(Dispatchers.IO) {

        val connection =
            (URL(CHAT_URL).openConnection() as HttpURLConnection)

        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 15000
            connection.readTimeout = 120000
            connection.doOutput = true

            connection.setRequestProperty(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            connection.setRequestProperty(
                "Accept",
                "application/json"
            )

            val payload = JSONObject()
                .put("message", message)
                .put("engineId", engineId)
                .put("useOrchestrator", engineId == "agent")
                .toString()

            connection.outputStream.use { output ->
                output.write(payload.toByteArray(Charsets.UTF_8))
                output.flush()
            }

            val status = connection.responseCode

            val responseStream =
                if (status in 200..299) {
                    connection.inputStream
                } else {
                    connection.errorStream
                }

            val responseText = responseStream
                ?.bufferedReader(Charsets.UTF_8)
                ?.use { it.readText() }
                .orEmpty()

            val json = try {
                JSONObject(responseText)
            } catch (_: Exception) {
                JSONObject()
            }

            if (status !in 200..299) {
                val error = json.optString(
                    "error",
                    "HTTP $status"
                )
                throw IllegalStateException(error)
            }

            json.optString("response")
                .ifBlank {
                    "وصل رد فارغ من خادم Lazaynova."
                }

        } finally {
            connection.disconnect()
        }
    }
}
