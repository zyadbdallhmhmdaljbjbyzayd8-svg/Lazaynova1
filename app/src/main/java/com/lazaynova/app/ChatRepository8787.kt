package com.lazaynova.app

import org.json.JSONObject

sealed class RepositoryOutcome<out T> {
    data class Success<T>(val data: T) : RepositoryOutcome<T>()
    data class Failure(val message: String, val statusCode: Int = -1) : RepositoryOutcome<Nothing>()
}

data class ChatReplyPayload(
    val replyText: String,
    val modelName: String?,
    val conversationId: String?,
    val latencyMs: Long
)

class ChatRepository8787(
    private val apiClient: BackendApiClient8787,
    private val tokenStore: SecureTokenStore
) {
    fun hasValidSession(): Boolean {
        val tok = tokenStore.getAccessToken() ?: return false
        return !tokenStore.isExpired()
    }

    fun currentAccountEmail(): String? = tokenStore.getAccountEmail()

    fun signOut() {
        tokenStore.clearSession()
    }

    suspend fun probeBackend(): RepositoryOutcome<String> {
        val res = apiClient.checkHealth()
        if (!res.ok) {
            return RepositoryOutcome.Failure(
                message = res.errorMessage ?: "تعذر الاتصال بالخادم على المنفذ 8787",
                statusCode = res.statusCode
            )
        }
        val label = try {
            val obj = JSONObject(res.rawBody)
            obj.optString("status").ifBlank { "healthy" }
        } catch (_: Exception) {
            "healthy"
        }
        return RepositoryOutcome.Success(label)
    }

    suspend fun fetchConversations(): RepositoryOutcome<List<ConversationSummary>> {
        val token = tokenStore.getAccessToken()
        val res = apiClient.listConversations(token)
        if (!res.ok) {
            return RepositoryOutcome.Failure(
                message = res.errorMessage ?: "تعذر جلب المحادثات من المنفذ 8787",
                statusCode = res.statusCode
            )
        }
        return RepositoryOutcome.Success(BackendApiClient8787.parseConversations(res.rawBody))
    }

    suspend fun createConversation(engineId: String, title: String? = null): RepositoryOutcome<ConversationSummary> {
        val token = tokenStore.getAccessToken()
        val res = apiClient.createConversation(token, engineId, title)
        if (!res.ok) {
            return RepositoryOutcome.Failure(
                message = res.errorMessage ?: "تعذر إنشاء محادثة جديدة على المنفذ 8787",
                statusCode = res.statusCode
            )
        }
        return try {
            val obj = JSONObject(res.rawBody)
            val convObj = obj.optJSONObject("conversation") ?: obj
            val id = convObj.optString("id")
            if (id.isBlank()) {
                RepositoryOutcome.Failure("استجابة إنشاء المحادثة لا تحتوي على معرف صالح", res.statusCode)
            } else {
                RepositoryOutcome.Success(
                    ConversationSummary(
                        id = id,
                        title = convObj.optString("title", title ?: "محادثة جديدة"),
                        engineId = convObj.optString("engineId", engineId)
                    )
                )
            }
        } catch (e: Exception) {
            RepositoryOutcome.Failure(e.message ?: "خطأ في قراءة استجابة المحادثة", res.statusCode)
        }
    }

    suspend fun fetchMessages(conversationId: String): RepositoryOutcome<List<ChatMessageItem>> {
        val token = tokenStore.getAccessToken()
        val res = apiClient.getMessages(token, conversationId)
        if (!res.ok) {
            return RepositoryOutcome.Failure(
                message = res.errorMessage ?: "تعذر جلب رسائل المحادثة",
                statusCode = res.statusCode
            )
        }
        return RepositoryOutcome.Success(BackendApiClient8787.parseMessages(res.rawBody))
    }

    suspend fun sendMessage(
        message: String,
        engineId: String,
        conversationId: String?
    ): RepositoryOutcome<ChatReplyPayload> {
        val start = System.currentTimeMillis()
        val token = tokenStore.getAccessToken()
        val res = apiClient.sendChat(token, message, engineId, conversationId)
        val elapsed = (System.currentTimeMillis() - start).coerceAtLeast(0L)

        if (!res.ok) {
            return RepositoryOutcome.Failure(
                message = res.errorMessage ?: "فشل إرسال الرسالة إلى المنفذ 8787",
                statusCode = res.statusCode
            )
        }

        return try {
            val obj = JSONObject(res.rawBody)
            val reply = obj.optString("reply").ifBlank {
                obj.optString("response").ifBlank {
                    obj.optJSONObject("message")?.optString("content") ?: ""
                }
            }
            if (reply.isBlank()) {
                RepositoryOutcome.Failure("تم استلام استجابة فارغة من الخادم على المنفذ 8787", res.statusCode)
            } else {
                RepositoryOutcome.Success(
                    ChatReplyPayload(
                        replyText = reply,
                        modelName = obj.optString("model", "").takeIf { it.isNotBlank() },
                        conversationId = obj.optString("conversationId", "").takeIf { it.isNotBlank() },
                        latencyMs = elapsed
                    )
                )
            }
        } catch (e: Exception) {
            RepositoryOutcome.Failure(e.message ?: "خطأ في تحليل رد الخادم", res.statusCode)
        }
    }
}
