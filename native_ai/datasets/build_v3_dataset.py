
"""Build a diverse Arabic/English dataset for LAZAYNOVA L3 V3.

Creates at least 150 distinct instruction-response pairs.
Does not overwrite existing datasets.
"""

import json
import hashlib
from pathlib import Path


OUTPUT = Path(
    "native_ai/datasets/sample_ar_v3.jsonl"
)


# Each row is an independently authored prompt and response.
# Format: (language, instruction, response)

DATA = [

# ---------------- ARABIC: PROGRAMMING ----------------

("ar", "ما المقصود بالبرمجة كائنية التوجه؟",
 "أسلوب برمجي ينظم البرنامج حول كائنات تجمع البيانات والوظائف التي تتعامل معها."),

("ar", "متى يكون استخدام الدوال مفيداً؟",
 "عندما تتكرر مهمة أو نريد تقسيم البرنامج إلى أجزاء صغيرة يسهل اختبارها وصيانتها."),

("ar", "ما الفرق بين القائمة والصف في Python؟",
 "القائمة قابلة للتعديل، بينما الصف غير قابل للتعديل بعد إنشائه."),

("ar", "لماذا نستخدم معالجة الاستثناءات؟",
 "للتعامل مع الأخطاء المتوقعة دون إنهاء البرنامج بصورة مفاجئة."),

("ar", "ما وظيفة حلقة for؟",
 "تكرار تنفيذ مجموعة تعليمات على عناصر متتابعة مثل عناصر قائمة أو نطاق أرقام."),

("ar", "كيف تعمل حلقة while؟",
 "تكرر تنفيذ التعليمات ما دام الشرط المحدد صحيحاً."),

("ar", "ما معنى المتغير المحلي؟",
 "متغير يُعرّف داخل دالة ويكون نطاق استخدامه مرتبطاً بتلك الدالة."),

("ar", "ما فائدة التعليقات في الكود؟",
 "تشرح الأجزاء المهمة من البرنامج وتساعد المطورين على فهم القرارات البرمجية."),

("ar", "ما المقصود بالبرمجة غير المتزامنة؟",
 "تنظيم العمليات بحيث يمكن انتظار المهام البطيئة دون حجب تنفيذ أعمال أخرى."),

("ar", "لماذا يجب التحقق من مدخلات المستخدم؟",
 "لمنع البيانات غير الصحيحة وتقليل الأخطاء والثغرات الناتجة عن المدخلات غير الموثوقة."),

("ar", "ما الفرق بين المترجم والمفسر؟",
 "المترجم يحول البرنامج إلى صيغة تنفيذية قبل التشغيل غالباً، أما المفسر فينفذ التعليمات عبر بيئة تفسير."),

("ar", "ما هي البنية الشجرية للبيانات؟",
 "هي بنية تتكون من عقد مترابطة بعلاقات أب وأبناء، وتناسب تمثيل البيانات الهرمية."),

("ar", "متى نستخدم القاموس في Python؟",
 "عندما نحتاج إلى تخزين قيم مرتبطة بمفاتيح فريدة للوصول السريع إليها."),

("ar", "ما المقصود بالاستدعاء الذاتي؟",
 "أن تستدعي الدالة نفسها لحل مشكلة إلى أن تصل إلى حالة توقف محددة."),

("ar", "كيف نختبر دالة صغيرة؟",
 "نمرر إليها مدخلات معروفة ونقارن النتائج الفعلية بالنتائج المتوقعة."),

# ---------------- ARABIC: COMPUTER SCIENCE ----------------

("ar", "ما وظيفة نظام التشغيل؟",
 "يدير موارد الجهاز ويوفر خدمات لتشغيل التطبيقات والتعامل مع الملفات والأجهزة."),

("ar", "ما الفرق بين الذاكرة المؤقتة RAM وذاكرة ROM؟",
 "RAM تستخدم أثناء تشغيل البرامج وتفقد محتواها عادة عند انقطاع الطاقة، أما ROM فتحتفظ بمحتوى ثابت أو شبه ثابت."),

("ar", "كيف ينتقل الملف عبر الشبكة؟",
 "يقسم إلى وحدات بيانات تُرسل عبر بروتوكولات الشبكة ثم يعاد تجميعها عند الطرف المستلم."),

("ar", "ما المقصود بعنوان IP؟",
 "عنوان منطقي يُستخدم لتحديد واجهة جهاز على شبكة تعتمد بروتوكول الإنترنت."),

("ar", "لماذا نستخدم DNS؟",
 "لتحويل أسماء النطاقات المقروءة مثل example.com إلى عناوين IP."),

("ar", "ما فائدة نظام الملفات؟",
 "ينظم تخزين الملفات والمجلدات وطرق الوصول إليها وإدارتها."),

("ar", "ما الفرق بين العملية والخيط البرمجي؟",
 "العملية برنامج قيد التنفيذ بموارده الخاصة، والخيط مسار تنفيذ داخل عملية."),

("ar", "ما المقصود بالتخزين المؤقت؟",
 "الاحتفاظ المؤقت بالبيانات كثيرة الاستخدام لتقليل زمن الوصول وتحسين الأداء."),

("ar", "كيف يعمل المعالج المركزي بصورة عامة؟",
 "يجلب التعليمات ويفك ترميزها وينفذ العمليات الحسابية والمنطقية وينظم تدفق التنفيذ."),

("ar", "ما معنى ضغط البيانات؟",
 "تمثيل البيانات بعدد أقل من البتات لتقليل مساحة التخزين أو حجم النقل."),

# ---------------- ARABIC: AI AND MACHINE LEARNING ----------------

("ar", "ما الفرق بين الذكاء الاصطناعي والتعلم الآلي؟",
 "الذكاء الاصطناعي مجال واسع، والتعلم الآلي أحد فروعه التي تستخلص الأنماط من البيانات."),

("ar", "ما المقصود ببيانات التدريب؟",
 "أمثلة يستخدمها النموذج لتعديل أوزانه وتعلم العلاقات والأنماط."),

("ar", "ما هي بيانات التقييم؟",
 "بيانات منفصلة تُستخدم لقياس أداء النموذج على أمثلة لم يتدرب عليها."),

("ar", "لماذا نقسم البيانات إلى تدريب واختبار؟",
 "لقياس قدرة النموذج على التعميم بدلاً من الاكتفاء بحفظ أمثلة التدريب."),

("ar", "ما معنى فرط التخصيص؟",
 "أن يتعلم النموذج تفاصيل بيانات التدريب بدرجة تجعله ضعيف الأداء على أمثلة جديدة."),

("ar", "ما وظيفة معدل التعلم؟",
 "يحدد حجم التغيير الذي يطبقه المحسن على أوزان النموذج في كل خطوة تدريب."),

("ar", "ما فائدة تقليم التدرجات؟",
 "يحد من كبر التدرجات ويساعد على استقرار التدريب عند حدوث انفجارات في قيمها."),

("ar", "ما المقصود بالنموذج اللغوي؟",
 "نموذج يتعلم أنماط اللغة ويستخدم سياق الرموز السابقة لتوقع الرموز التالية."),

("ar", "لماذا تحتاج النماذج إلى Tokenizer؟",
 "لتحويل النص إلى رموز رقمية يمكن للنموذج معالجتها."),

("ar", "ما فائدة آلية الانتباه؟",
 "تساعد النموذج على إعطاء أوزان مختلفة لأجزاء السياق عند معالجة كل موضع."),

("ar", "ما المقصود بالاستدلال في الذكاء الاصطناعي؟",
 "استخدام نموذج مدرب لإنتاج تنبؤ أو إجابة انطلاقاً من مدخل جديد."),

("ar", "هل انخفاض خسارة التدريب يثبت جودة النموذج؟",
 "لا، يجب أيضاً قياس الأداء على بيانات تقييم مستقلة وفحص جودة المخرجات."),

("ar", "كيف نكتشف تكرار الإجابات في النموذج؟",
 "نختبر عدة مطالبات متنوعة ونقيس تكرار الرموز والكلمات والجمل في المخرجات."),

("ar", "ما الفرق بين التدريب والاستدلال؟",
 "التدريب يعدل أوزان النموذج، أما الاستدلال فيستخدم الأوزان الحالية لإنتاج مخرجات."),

("ar", "لماذا نحتاج إلى مجموعة بيانات متنوعة؟",
 "لتعريض النموذج لمفردات وسياقات وأساليب متعددة وتحسين قدرته على التعميم."),

# ---------------- ARABIC: SECURITY AND PRIVACY ----------------

("ar", "ما المقصود بالتشفير؟",
 "تحويل البيانات إلى صيغة لا يمكن فهمها دون مفتاح أو وسيلة فك مناسبة."),

("ar", "ما الفرق بين التشفير والتجزئة؟",
 "التشفير قابل للعكس بمفتاح مناسب، أما التجزئة فتنتج بصمة لا يُفترض عكسها عملياً."),

("ar", "كيف نصمم كلمة مرور قوية؟",
 "نستخدم كلمة طويلة وفريدة وغير مرتبطة بمعلومات شخصية سهلة التخمين."),

("ar", "لماذا لا ينبغي حفظ كلمات المرور كنص صريح؟",
 "لأن تسرب قاعدة البيانات سيكشف كلمات المستخدمين مباشرة."),

("ar", "ما وظيفة المصادقة متعددة العوامل؟",
 "تضيف دليلاً آخر للهوية بجانب كلمة المرور لتقليل أثر سرقتها."),

("ar", "ما معنى مبدأ أقل صلاحية؟",
 "منح كل مستخدم أو عملية أقل مجموعة صلاحيات لازمة لأداء مهمتها."),

("ar", "كيف نحمي واجهة API؟",
 "نستخدم المصادقة والتحقق من المدخلات وتحديد المعدل وتسجيل الأحداث وتقييد الصلاحيات."),

("ar", "ما المقصود بالنسخ الاحتياطي؟",
 "إنشاء نسخة منفصلة من البيانات لاستعادتها عند الفقد أو التلف."),

("ar", "لماذا يجب إخفاء مفاتيح API؟",
 "لأن كشفها قد يسمح للآخرين باستخدام الحساب أو الخدمة بصلاحيات صاحب المفتاح."),

("ar", "ما فائدة تحديث البرامج؟",
 "يسد الثغرات المعروفة ويصلح الأخطاء ويحسن التوافق والاستقرار."),

# ---------------- ARABIC: SCIENCE AND MATH ----------------

("ar", "ما الفرق بين الكتلة والوزن؟",
 "الكتلة مقدار المادة، أما الوزن فهو قوة الجاذبية المؤثرة في الجسم."),

("ar", "لماذا يتغير لون السماء خلال الغروب؟",
 "لأن الضوء يقطع مسافة أطول في الغلاف الجوي، فيتشتت الضوء الأزرق أكثر ويبقى الأحمر والبرتقالي أوضح."),

("ar", "ما المقصود بالطاقة الحركية؟",
 "هي الطاقة التي يمتلكها الجسم بسبب حركته، وتزداد بزيادة كتلته أو مربع سرعته."),

("ar", "كيف نحسب مساحة المستطيل؟",
 "نضرب الطول في العرض بعد التأكد من استخدام وحدات متوافقة."),

("ar", "ما معنى العدد الأولي؟",
 "عدد صحيح أكبر من واحد لا يقبل القسمة دون باق إلا على الواحد وعلى نفسه."),

("ar", "ما الفرق بين التغير الفيزيائي والكيميائي؟",
 "التغير الفيزيائي يغير الشكل أو الحالة دون تكوين مادة جديدة، والكيميائي ينتج مواد مختلفة."),

("ar", "لماذا تحتاج النباتات إلى الضوء؟",
 "تستخدم الطاقة الضوئية في عملية البناء الضوئي لصنع المواد العضوية."),

("ar", "ما وظيفة الجهاز العصبي؟",
 "ينقل المعلومات ويعالجها وينسق استجابات الجسم للمؤثرات."),

("ar", "ما المقصود بالدورة المائية؟",
 "حركة الماء بين سطح الأرض والغلاف الجوي عبر التبخر والتكاثف والهطول والجريان."),

("ar", "كيف نميز بين الحقيقة والفرضية العلمية؟",
 "الحقيقة مدعومة بملاحظات وأدلة متكررة، والفرضية تفسير قابل للاختبار والتفنيد."),

# ---------------- ARABIC: REASONING AND LEARNING ----------------

("ar", "كيف تقارن بين حلين لمشكلة واحدة؟",
 "نحدد معايير مثل الدقة والتكلفة والوقت والمخاطر، ثم نقيس الحلين وفق المعايير نفسها."),

("ar", "ماذا تفعل عندما لا تعرف إجابة سؤال؟",
 "أحدد ما هو معروف وما هو مجهول، ثم أبحث عن دليل موثوق وأصرح بعدم اليقين إن بقي."),

("ar", "كيف تحول هدفاً كبيراً إلى خطة عملية؟",
 "أقسمه إلى نتائج صغيرة قابلة للقياس، وأحدد لكل نتيجة موعداً وخطوة تنفيذ."),

("ar", "لماذا ندوّن نتائج التجارب؟",
 "حتى يمكن مراجعة الإجراءات ومقارنة النتائج وإعادة التجربة والتحقق منها."),

("ar", "كيف تتعلم مفهوماً صعباً؟",
 "ابدأ بتعريف بسيط، ثم مثال عملي، وبعده تمرين مستقل يختبر فهمك."),

("ar", "ما فائدة التفكير النقدي؟",
 "يساعد على تقييم الأدلة وكشف الافتراضات والتمييز بين الرأي والمعلومة المدعومة."),

("ar", "كيف تتعامل مع معلومة متضاربة؟",
 "أراجع المصادر الأصلية وتاريخ النشر والمنهج والأدلة قبل ترجيح أحد الادعاءات."),

("ar", "ما معنى قابلية إعادة التجربة؟",
 "أن يستطيع شخص آخر اتباع الإجراءات نفسها ومحاولة الوصول إلى نتائج متوافقة."),

("ar", "كيف نحدد أولوية المهام؟",
 "نقارن أثر كل مهمة ودرجة استعجالها والموارد اللازمة لتنفيذها."),

("ar", "لماذا نراجع العمل قبل تسليمه؟",
 "لاكتشاف الأخطاء والتحقق من استيفاء المتطلبات وتقليل إعادة العمل."),

# ---------------- ENGLISH: PROGRAMMING ----------------

("en", "What is dependency injection?",
 "It is a design technique in which a component receives the dependencies it needs instead of constructing them internally."),

("en", "Why should functions have a single responsibility?",
 "Focused functions are easier to understand, test, reuse, and change safely."),

("en", "What is an immutable object?",
 "It is an object whose observable state cannot be changed after creation."),

("en", "When is a hash map useful?",
 "It is useful when values need to be retrieved efficiently through unique keys."),

("en", "What does a database transaction provide?",
 "It groups operations so they can succeed together or be rolled back according to transaction rules."),

("en", "Why are integration tests important?",
 "They verify that multiple components work together across their interfaces."),

("en", "What is a race condition?",
 "It occurs when the result depends on the unpredictable timing or ordering of concurrent operations."),

("en", "How does a queue differ from a stack?",
 "A queue normally uses first-in first-out ordering, while a stack uses last-in first-out ordering."),

("en", "What is an application programming interface?",
 "An API defines how software components exchange requests, data, and results."),

("en", "Why should errors include useful context?",
 "Context helps developers identify the failing operation and diagnose the underlying cause."),

("en", "What is a package manager?",
 "It installs, updates, removes, and resolves dependencies for software packages."),

("en", "What is semantic versioning?",
 "It communicates compatibility changes through major, minor, and patch version numbers."),

("en", "Why use environment variables for configuration?",
 "They separate deployment-specific settings from source code and reduce the need to hard-code secrets."),

("en", "What is a memory leak?",
 "It occurs when a program retains memory that it no longer needs and cannot release."),

("en", "How can code reviews improve software quality?",
 "They help identify defects, clarify design decisions, and share knowledge among developers."),

# ---------------- ENGLISH: SYSTEMS ----------------

("en", "What is virtual memory?",
 "It gives processes an address space that the operating system maps to physical memory and storage as needed."),

("en", "What is the purpose of a CPU cache?",
 "It keeps frequently accessed data close to the processor to reduce average memory access time."),

("en", "What does a network router do?",
 "It forwards packets between networks using routing information."),

("en", "Why is time synchronization important in distributed systems?",
 "Consistent time references make logs, certificates, coordination, and event analysis more reliable."),

("en", "What is a file descriptor?",
 "It is a process-level reference used by an operating system to access an open file or another resource."),

("en", "What is the difference between TCP and UDP?",
 "TCP provides an ordered reliable byte stream, while UDP sends datagrams without built-in delivery guarantees."),

("en", "Why do systems use checksums?",
 "Checksums help detect accidental corruption during storage or transmission."),

("en", "What is a process scheduler?",
 "It decides which runnable process or thread receives CPU time."),

("en", "What is a symbolic link?",
 "It is a filesystem entry that refers to another path."),

("en", "Why is disk space monitoring useful?",
 "It helps prevent failures caused by applications being unable to write required files."),

# ---------------- ENGLISH: MACHINE LEARNING ----------------

("en", "What is a validation dataset?",
 "It is a separate dataset used to compare training choices and tune model settings."),

("en", "What does a learning rate scheduler do?",
 "It changes the learning rate during training according to a defined schedule."),

("en", "Why use gradient accumulation?",
 "It combines gradients across smaller batches to approximate training with a larger effective batch."),

("en", "What is teacher forcing?",
 "It trains a sequence model using the expected previous token as context during training."),

("en", "What is an embedding vector?",
 "It is a numerical representation that maps an item into a continuous vector space."),

("en", "What does cross-entropy loss measure?",
 "It measures the difference between a target probability distribution and a model prediction."),

("en", "Why can a model have low training loss but poor outputs?",
 "It may memorize examples, learn dataset artifacts, or fail to generalize to unseen prompts."),

("en", "What is inference latency?",
 "It is the time required for a model to produce an output after receiving an input."),

("en", "Why should evaluation examples be held out?",
 "Keeping them out of training gives a less biased estimate of performance on unseen data."),

("en", "What is token sampling temperature?",
 "It controls how sharply or broadly a model samples from its next-token probability distribution."),

("en", "What is beam search?",
 "It explores several high-scoring candidate sequences instead of selecting only one token at each step."),

("en", "Why can repetition penalties affect fluency?",
 "Strong penalties may suppress useful repeated words or byte patterns and make output less natural."),

("en", "What is model quantization?",
 "It represents model values with lower-precision numbers to reduce memory use and sometimes improve inference speed."),

("en", "Why does a tokenizer need a stable vocabulary?",
 "Training and inference must interpret token IDs consistently for the learned weights to remain meaningful."),

("en", "What is an autoregressive language model?",
 "It generates a sequence by predicting each next token from the preceding context."),

# ---------------- ENGLISH: SECURITY ----------------

("en", "What is a threat model?",
 "It identifies valuable assets, possible attackers, attack paths, and security controls."),

("en", "Why should authentication and authorization be separate?",
 "Authentication verifies identity, while authorization decides what that identity is allowed to do."),

("en", "What is a salt in password hashing?",
 "It is a unique random value added before hashing to make precomputed attacks less effective."),

("en", "Why should applications validate file uploads?",
 "Validation reduces risks from unexpected formats, oversized files, and malicious content."),

("en", "What is the principle of defense in depth?",
 "It uses multiple independent security controls so one failure does not expose the entire system."),

("en", "Why rotate compromised credentials?",
 "Replacing exposed credentials prevents continued use of the compromised secret."),

("en", "What is rate limiting?",
 "It restricts how frequently a client can make requests within a defined period."),

("en", "Why should logs avoid storing secrets?",
 "Logs may be widely accessible or retained for long periods, increasing the impact of a leak."),

("en", "What is a software supply chain attack?",
 "It compromises a dependency, build process, update channel, or another part of software delivery."),

("en", "Why are security patches time-sensitive?",
 "Known vulnerabilities may be actively exploited before affected systems are updated."),

# ---------------- ENGLISH: SCIENCE AND MATH ----------------

("en", "What is the scientific method?",
 "It is a structured process of asking questions, forming testable explanations, gathering evidence, and revising conclusions."),

("en", "What is the difference between speed and velocity?",
 "Speed is scalar distance per time, while velocity includes direction."),

("en", "Why does ice float on liquid water?",
 "Solid water has a lower density than liquid water under ordinary conditions because of its crystal structure."),

("en", "What is a logarithm?",
 "It answers the question of what exponent is needed to produce a given number from a chosen base."),

("en", "What does statistical variance describe?",
 "It measures how far values are spread around their mean, using squared deviations."),

("en", "What is the conservation of energy?",
 "It states that energy is not created or destroyed in an isolated system, although it can change form."),

("en", "Why do seasons occur?",
 "They result mainly from Earth's axial tilt as Earth travels around the Sun."),

("en", "What is a chemical catalyst?",
 "It increases a reaction rate by providing an alternative pathway with lower activation energy."),

("en", "What is an ecosystem?",
 "It is a community of organisms interacting with one another and with their physical environment."),

("en", "Why is correlation not proof of causation?",
 "Two variables can move together because of coincidence, confounding factors, or another underlying cause."),

# ---------------- ENGLISH: REASONING AND PRACTICE ----------------

("en", "How should an uncertain claim be evaluated?",
 "Check the original evidence, source reliability, publication date, and whether independent sources support it."),

("en", "What makes a good experiment?",
 "It uses a clear question, controlled conditions, measurable outcomes, and a procedure that others can repeat."),

("en", "How can a large task become manageable?",
 "Break it into small deliverables, define completion criteria, and verify each deliverable independently."),

("en", "Why document failed experiments?",
 "Failures reveal constraints and prevent the same ineffective approach from being repeated."),

("en", "How do you choose between two technical designs?",
 "Compare correctness, security, complexity, resource use, maintainability, and measured performance."),

("en", "What is an assumption in problem solving?",
 "It is a condition accepted temporarily without proof and should be checked when it affects the result."),

("en", "Why are reproducible builds valuable?",
 "They make it easier to verify that the same source and environment produce equivalent artifacts."),

("en", "How can a team reduce accidental scope changes?",
 "Record requirements, agree on boundaries, review proposed changes, and test against the original acceptance criteria."),

("en", "What is a useful debugging strategy?",
 "Reproduce the issue, reduce it to a small case, inspect evidence, change one factor, and retest."),

("en", "Why should conclusions distinguish evidence from opinion?",
 "This makes uncertainty visible and allows readers to evaluate the reasoning independently."),


    ("ar", "كيف تعمل قاعدة البيانات العلائقية؟",
     "تنظم البيانات في جداول مترابطة، وتستخدم المفاتيح والعلاقات والاستعلامات لإدارتها."),

    ("ar", "ما الفرق بين المفتاح الأساسي والمفتاح الخارجي؟",
     "المفتاح الأساسي يميز كل سجل في جدوله، والمفتاح الخارجي يشير إلى سجل مرتبط في جدول آخر."),

    ("ar", "لماذا نستخدم فهارس قواعد البيانات؟",
     "تسرع البحث عن السجلات، لكنها تحتاج مساحة إضافية وقد تزيد تكلفة عمليات التعديل."),

    ("ar", "ما المقصود بهندسة البرمجيات؟",
     "هي تطبيق منهجي لمبادئ التصميم والتطوير والاختبار والصيانة لبناء برامج موثوقة."),

    ("ar", "كيف نقلل استهلاك الذاكرة في تطبيق؟",
     "نقيس الاستهلاك أولاً، ونتجنب الاحتفاظ غير الضروري بالبيانات، ونحرر الموارد بعد استخدامها."),

    ("ar", "ما فائدة واجهة سطر الأوامر؟",
     "تتيح تشغيل الأدوات وتمرير الخيارات وتنفيذ المهام بطريقة قابلة للأتمتة."),

    ("ar", "ما المقصود بالتوافق العكسي؟",
     "قدرة إصدار جديد من برنامج أو واجهة على الاستمرار في دعم الاستخدامات التي كانت تعمل في إصدار سابق."),

    ("ar", "كيف نتحقق من سلامة ملف تم تنزيله؟",
     "نحسب بصمته الرقمية مثل SHA-256 ونقارنها ببصمة موثوقة منشورة من المصدر."),

    ("ar", "ما الفرق بين الاختبار الوحدوي واختبار النظام؟",
     "يفحص الاختبار الوحدوي جزءاً صغيراً منفرداً، بينما يتحقق اختبار النظام من سلوك التطبيق المتكامل."),

    ("ar", "لماذا نستخدم التوثيق الآلي للواجهات؟",
     "يساعد المطورين على فهم المسارات والطلبات والاستجابات والمتطلبات دون تخمين."),

    ("en", "What is database normalization?",
     "It organizes relational data to reduce unnecessary duplication and improve data integrity."),

    ("en", "Why are database migrations versioned?",
     "Versioned migrations make schema changes traceable and allow environments to be updated consistently."),

    ("en", "What is continuous integration?",
     "It automatically builds and tests proposed code changes so defects can be detected early."),

    ("en", "How does a mutex help concurrent programs?",
     "A mutex allows only one thread at a time to enter a protected critical section."),

    ("en", "What is a RESTful resource?",
     "It is a named piece of application data exposed through a consistent HTTP interface."),

    ("en", "Why should software use structured logging?",
     "Structured fields make logs easier to filter, search, aggregate, and analyze automatically."),

    ("en", "What is an atomic file write?",
     "It publishes a completed file as one operation so readers do not observe a partially written result."),

    ("en", "What is the purpose of a software license?",
     "It defines the permissions and conditions under which software may be used, modified, and redistributed."),

    ("en", "How can mobile applications reduce battery consumption?",
     "They can limit background work, batch network requests, avoid unnecessary wakeups, and profile expensive operations."),

    ("en", "What is an acceptance test?",
     "It checks whether a delivered feature satisfies the behavior and conditions agreed upon by its stakeholders."),

]


def normalize(value):
    return " ".join(value.casefold().split())


def main():
    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Never overwrite an existing dataset.
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing dataset: {OUTPUT}"
        )

    prompts = set()
    pairs = set()
    rows = []

    for language, instruction, response in DATA:
        instruction = instruction.strip()
        response = response.strip()

        if not instruction or not response:
            raise ValueError("Empty instruction or response")

        normalized_prompt = normalize(instruction)
        normalized_pair = (
            normalized_prompt,
            normalize(response),
        )

        if normalized_prompt in prompts:
            raise ValueError(
                f"Duplicate prompt detected: {instruction}"
            )

        if normalized_pair in pairs:
            raise ValueError(
                f"Duplicate conversation detected: {instruction}"
            )

        prompts.add(normalized_prompt)
        pairs.add(normalized_pair)

        rows.append({
            "instruction": instruction,
            "response": response,
            "language": language,
        })

    if len(rows) < 150:
        raise ValueError(
            f"Dataset too small: {len(rows)} records"
        )

    arabic_count = sum(
        row["language"] == "ar" for row in rows
    )

    english_count = sum(
        row["language"] == "en" for row in rows
    )

    if arabic_count < 50 or english_count < 50:
        raise ValueError(
            "Both languages must have at least 50 records"
        )

    content = "".join(
        json.dumps(
            row,
            ensure_ascii=False,
        ) + "\n"
        for row in rows
    )

    # Write atomically without replacing an existing target.
    temporary = OUTPUT.with_name(
        OUTPUT.name + ".tmp"
    )

    if temporary.exists():
        raise FileExistsError(
            f"Temporary output already exists: {temporary}"
        )

    try:
        with temporary.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            stream.write(content)
            stream.flush()

        # Recheck target before publication.
        if OUTPUT.exists():
            raise FileExistsError(OUTPUT)

        temporary.rename(OUTPUT)

    except Exception:
        # Keep the temporary file for inspection if publication fails.
        raise

    digest = hashlib.sha256(
        OUTPUT.read_bytes()
    ).hexdigest()

    print("LAZAYNOVA V3 DATASET CREATED")
    print("Path:", OUTPUT)
    print("Total records:", len(rows))
    print("Arabic records:", arabic_count)
    print("English records:", english_count)
    print("Unique prompts:", len(prompts))
    print("Unique pairs:", len(pairs))
    print("SHA256:", digest)
    print("Dataset bytes:", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()

