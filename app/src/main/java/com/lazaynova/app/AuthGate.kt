package com.lazaynova.app

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.launch

@Composable
fun LazaynovaAuthGate(
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val activity = context as? Activity
    val scope = rememberCoroutineScope()
    val credentialManager = remember {
        CredentialManager.create(context)
    }

    var checking by remember { mutableStateOf(true) }
    var busy by remember { mutableStateOf(false) }
    var authenticated by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        val session = AuthSessionManager.restore(context)
        authenticated = session != null
        checking = false
    }

    if (authenticated) {
        content()
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "LAZAYNOVA AI",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )

        Spacer(Modifier.height(10.dp))

        Text(
            text = "Private. Autonomous. Yours.",
            color = MaterialTheme.colorScheme.onSurface
        )

        Spacer(Modifier.height(32.dp))

        when {
            checking || busy -> {
                CircularProgressIndicator()
                Spacer(Modifier.height(12.dp))
                Text("جارٍ التحقق من الحساب...")
            }

            else -> {
                Button(
                    enabled = activity != null &&
                        BuildConfig.GOOGLE_WEB_CLIENT_ID.isNotBlank(),
                    onClick = {
                        error = null
                        busy = true

                        scope.launch {
                            try {
                                val googleOption =
                                    GetGoogleIdOption.Builder()
                                        .setFilterByAuthorizedAccounts(false)
                                        .setServerClientId(
                                            BuildConfig.GOOGLE_WEB_CLIENT_ID
                                        )
                                        .setAutoSelectEnabled(false)
                                        .build()

                                val request =
                                    GetCredentialRequest.Builder()
                                        .addCredentialOption(googleOption)
                                        .build()

                                val result = credentialManager.getCredential(
                                    context = activity!!,
                                    request = request
                                )

                                val credential = result.credential

                                if (
                                    credential !is CustomCredential ||
                                    credential.type !=
                                    GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
                                ) {
                                    throw IllegalStateException(
                                        "لم يتم استلام بيانات اعتماد Google."
                                    )
                                }

                                val googleCredential =
                                    GoogleIdTokenCredential.createFrom(
                                        credential.data
                                    )

                                val session = AuthApi.googleLogin(
                                    googleCredential.idToken
                                )

                                AuthSessionManager.save(context, session)
                                authenticated = true
                            } catch (exception: Exception) {
                                error = exception.message
                                    ?: "تعذر تسجيل الدخول."
                            } finally {
                                busy = false
                            }
                        }
                    },
                    modifier = Modifier.width(260.dp)
                ) {
                    Text("المتابعة باستخدام Google")
                }

                if (BuildConfig.GOOGLE_WEB_CLIENT_ID.isBlank()) {
                    Text(
                        "إعداد Google Client ID غير مكتمل في Gradle.",
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
        }

        if (!error.isNullOrBlank()) {
            Spacer(Modifier.height(18.dp))
            Text(
                text = error!!,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}
