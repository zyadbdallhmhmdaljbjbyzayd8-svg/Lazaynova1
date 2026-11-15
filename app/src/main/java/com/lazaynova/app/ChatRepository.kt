package com.lazaynova.app

class ChatRepository {
    suspend fun sendMessage(
        message: String,
        conversationId: String?,
        engine: String
    ): ChatReply {
        return ApiClient.chat(
            message = message,
            engine = engine,
            conversationId = conversationId
        )
    }

    suspend fun authenticate(
        username: String,
        password: String,
        register: Boolean
    ): String {
        return ApiClient.authenticate(username, password, register)
    }

    suspend fun getConversationMessages(conversationId: String): List<ChatMessage> {
        return ApiClient.getConversationMessages(conversationId)
    }
}
