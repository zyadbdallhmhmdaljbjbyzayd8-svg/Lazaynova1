const API_BASE = (window.LAZAYNOVA_API_BASE || "").replace(/\/$/, "");
const form=document.querySelector("#chat-form"),input=document.querySelector("#message"),send=document.querySelector("#send");
const welcome=document.querySelector("#welcome"),chatArea=document.querySelector("#chat-area"),messagesEl=document.querySelector("#messages");
const history=[];
function addMessage(role,text,intent){const article=document.createElement("article");article.className=`message ${role}`;const label=document.createElement("small");label.textContent=role==="user"?"أنت":`Lazaynova${intent?` · ${intent}`:""}`;const body=document.createElement("div");body.textContent=text;article.append(label,body);messagesEl.append(article);chatArea.hidden=false;welcome.hidden=true;article.scrollIntoView({behavior:"smooth",block:"end"});}
function usePrompt(prompt){input.value=prompt;input.focus();}
document.querySelectorAll("[data-prompt]").forEach(button=>button.addEventListener("click",()=>usePrompt(button.dataset.prompt)));
document.querySelector("#new-chat").addEventListener("click",()=>{history.length=0;messagesEl.replaceChildren();chatArea.hidden=true;welcome.hidden=false;input.value="";});
form.addEventListener("submit",async event=>{event.preventDefault();const message=input.value.trim();if(!message)return;input.value="";addMessage("user",message);history.push({role:"user",content:message});send.disabled=true;
try{if(!API_BASE)throw new Error("واجهة الويب جاهزة، لكن عنوان API غير مضبوط. عيّن window.LAZAYNOVA_API_BASE في app.js بعد نشر الخادم.");
const response=await fetch(`${API_BASE}/api/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message,language:"ar",history:history.slice(-10)})});
const data=await response.json();if(!response.ok)throw new Error(data.error||"فشل الطلب إلى الخادم");const reply=data.reply||"لم يصل رد.";history.push({role:"assistant",content:reply});addMessage("assistant",reply,data.intent);
}catch(error){addMessage("assistant",`تعذّر تنفيذ الطلب: ${error.message}`); }finally{send.disabled=false;input.focus();}});
