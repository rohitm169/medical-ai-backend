"""
============================================
GEMINI AI SERVICE (ENHANCED WITH WEB CONTEXT)
============================================
Integration with Google Gemini AI for medical
symptom analysis with web search context support.
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from PIL import Image
import io


# ============================================
# GEMINI SERVICE CLASS
# ============================================
class GeminiService:
    """Service class for Gemini AI operations with web context"""

    # ============================================
    # CONFIGURATION
    # ============================================
    MODEL_TEXT = 'gemini-2.5-flash'
    MODEL_VISION = 'gemini-2.5-flash'

    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 8192
    DEFAULT_TIMEOUT = 90

    CHAT_TEMPERATURE = 0.8
    CHAT_MAX_TOKENS = 2048

    SAFETY_SETTINGS = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        }
    ]


    # ============================================
    # INITIALIZE GEMINI
    # ============================================
    @staticmethod
    def initialize():
        """Initialize Gemini API with API key"""

        api_key = os.getenv('GEMINI_API_KEY')

        if not api_key:
            raise Exception('GEMINI_API_KEY not configured')

        try:
            genai.configure(api_key=api_key)
            return True

        except Exception as e:
            print(f"[GEMINI INIT ERROR] {str(e)}")
            raise Exception(f'Failed to initialize Gemini: {str(e)}')


    # ============================================
    # GET LANGUAGE INSTRUCTION (NEW)
    # ============================================
    @staticmethod
    def get_language_instruction(language: str) -> str:
        """
        Get language-specific instruction for AI.

        Args:
            language: Language code (en/hi/bn/hinglish/benglish/auto)

        Returns:
            Language instruction string
        """

        instructions = {
            'en': """LANGUAGE INSTRUCTION:
Respond ONLY in English. Use clear, simple language that anyone can understand.
Use professional medical terminology when needed but always explain it.""",

            'hi': """LANGUAGE INSTRUCTION:
हिन्दी में जवाब दें (Respond ONLY in Hindi - हिन्दी).
Use Devanagari script (देवनागरी लिपि) for Hindi text.
Use simple, easy-to-understand Hindi.
Medical terms can be in English but explain in Hindi.
Example: "आपको tension headache (तनाव सिरदर्द) हो रहा है।"
Be culturally sensitive and use respectful tone (आप, आपको).""",

            'bn': """LANGUAGE INSTRUCTION:
বাংলায় উত্তর দিন (Respond ONLY in Bengali - বাংলা).
Use Bengali script (বাংলা লিপি) for Bengali text.
Use simple, easy-to-understand Bengali.
Medical terms can be in English but explain in Bengali.
Example: "আপনার tension headache (টেনশন মাথাব্যথা) হচ্ছে।"
Be culturally sensitive and use respectful tone (আপনি, আপনাকে).""",

            'hinglish': """LANGUAGE INSTRUCTION:
Respond in HINGLISH (Hindi written in English/Roman script).
Mix Hindi and English naturally as Indians speak.
Use English script (Roman) for both Hindi and English words.
Examples:
- "Aapko tension headache ho raha hai jo bahut common hai."
- "Mai aapko kuch home remedies suggest karta hun."
- "Doctor ke paas jaana zaroori nahi hai abhi."
Use casual, friendly tone like talking to a friend.
Mix English medical terms naturally: "Yeh chronic problem nahi hai."
DO NOT use Devanagari script. ONLY Roman/English letters.""",

            'benglish': """LANGUAGE INSTRUCTION:
Respond in BENGLISH (Bengali written in English/Roman script).
Mix Bengali and English naturally as Bengalis speak.
Use English script (Roman) for both Bengali and English words.
Examples:
- "Apnar tension headache hocche ja khub common."
- "Ami apnake kichu home remedies suggest korchi."
- "Ekhon doctor er kache jaowa zaruri na."
Use respectful, friendly tone (apni, apnake).
Mix English medical terms naturally: "Eta chronic problem na."
DO NOT use Bengali script (বাংলা). ONLY Roman/English letters.""",

            'auto': """LANGUAGE INSTRUCTION:
DETECT the language from the user's question and respond in the SAME language.
- If user writes in English → respond in English
- If user writes in Hindi (हिन्दी) → respond in Hindi (हिन्दी)
- If user writes in Bengali (বাংলা) → respond in Bengali (বাংলা)
- If user writes in Hinglish → respond in Hinglish (Roman script)
- If user writes in Benglish → respond in Benglish (Roman script)
- If mixed languages → use the dominant language

Match the user's writing style and tone."""
        }

        return instructions.get(language, instructions['en'])


    # ============================================
    # ANALYZE TEXT SYMPTOMS (WITH WEB CONTEXT)
    # ============================================
    @staticmethod
    def analyze_symptoms(
        symptoms_text: str,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        duration: Optional[str] = None,
        additional_notes: Optional[str] = None,
        web_context: Optional[str] = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Analyze text symptoms using Gemini AI with optional web context.

        Args:
            symptoms_text: User's symptoms
            age: Patient age
            gender: Patient gender
            duration: Symptom duration
            additional_notes: Extra info
            web_context: Web search results context
            language: Response language code

        Returns:
            Analysis result dictionary
        """

        try:
            GeminiService.initialize()

            prompt = GeminiService.build_text_prompt(
                symptoms_text=symptoms_text,
                age=age,
                gender=gender,
                duration=duration,
                additional_notes=additional_notes,
                web_context=web_context
            )

            # Add language instruction
            language_instruction = GeminiService.get_language_instruction(language)
            prompt = f"{language_instruction}\n\n{prompt}"

            model = genai.GenerativeModel(
                model_name=GeminiService.MODEL_TEXT,
                generation_config={
                    'temperature': GeminiService.DEFAULT_TEMPERATURE,
                    'max_output_tokens': GeminiService.DEFAULT_MAX_TOKENS
                },
                safety_settings=GeminiService.SAFETY_SETTINGS
            )

            response = model.generate_content(prompt)

            if not response or not response.text:
                return {
                    'success': False,
                    'error': 'Empty response from Gemini'
                }

            parsed_data = GeminiService.parse_response(response.text)

            if not parsed_data:
                return {
                    'success': False,
                    'error': 'Failed to parse AI response'
                }

            return {
                'success': True,
                'data': parsed_data,
                'raw_response': response.text
            }

        except Exception as e:
            print(f"[ANALYZE SYMPTOMS ERROR] {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


    # ============================================
    # ANALYZE SINGLE IMAGE
    # ============================================
    @staticmethod
    def analyze_image(
        image_bytes: bytes,
        image_type: str = 'other',
        symptoms_context: Optional[str] = None,
        web_context: Optional[str] = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Analyze a medical image using Gemini Vision with web context.

        Args:
            image_bytes: Image binary data
            image_type: Type of image (skin/eye/throat)
            symptoms_context: Optional symptoms text
            web_context: Web search context
            language: Response language code

        Returns:
            Analysis result dictionary
        """

        try:
            GeminiService.initialize()

            try:
                image = Image.open(io.BytesIO(image_bytes))

                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')

            except Exception as e:
                return {
                    'success': False,
                    'error': f'Invalid image data: {str(e)}'
                }

            prompt = GeminiService.build_image_prompt(
                image_type=image_type,
                symptoms_context=symptoms_context,
                web_context=web_context
            )

            # Add language instruction
            language_instruction = GeminiService.get_language_instruction(language)
            prompt = f"{language_instruction}\n\n{prompt}"

            model = genai.GenerativeModel(
                model_name=GeminiService.MODEL_VISION,
                generation_config={
                    'temperature': GeminiService.DEFAULT_TEMPERATURE,
                    'max_output_tokens': GeminiService.DEFAULT_MAX_TOKENS
                },
                safety_settings=GeminiService.SAFETY_SETTINGS
            )

            response = model.generate_content([prompt, image])

            if not response or not response.text:
                return {
                    'success': False,
                    'error': 'Empty response from Gemini Vision'
                }

            parsed_data = GeminiService.parse_response(response.text)

            if not parsed_data:
                return {
                    'success': False,
                    'error': 'Failed to parse AI response'
                }

            return {
                'success': True,
                'data': parsed_data,
                'raw_response': response.text
            }

        except Exception as e:
            print(f"[ANALYZE IMAGE ERROR] {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


    # ============================================
    # ANALYZE SYMPTOMS WITH IMAGES
    # ============================================
    @staticmethod
    def analyze_symptoms_with_images(
        symptoms_text: str,
        images: List[Dict[str, Any]],
        age: Optional[int] = None,
        gender: Optional[str] = None,
        duration: Optional[str] = None,
        additional_notes: Optional[str] = None,
        web_context: Optional[str] = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Analyze symptoms combined with medical images.

        Args:
            symptoms_text: User's symptoms
            images: List of image dicts
            age: Patient age
            gender: Patient gender
            duration: Symptom duration
            additional_notes: Extra info
            web_context: Web search context
            language: Response language code

        Returns:
            Analysis result dictionary
        """

        try:
            GeminiService.initialize()

            pil_images = []
            image_descriptions = []

            for idx, img in enumerate(images):
                try:
                    img_bytes = img.get('bytes')
                    img_type = img.get('type', 'other')

                    if not img_bytes:
                        continue

                    pil_img = Image.open(io.BytesIO(img_bytes))

                    if pil_img.mode not in ('RGB', 'L'):
                        pil_img = pil_img.convert('RGB')

                    pil_images.append(pil_img)
                    image_descriptions.append(f"Image {idx + 1}: {img_type}")

                except Exception as e:
                    print(f"[IMAGE CONVERT ERROR] {str(e)}")
                    continue

            if not pil_images:
                return GeminiService.analyze_symptoms(
                    symptoms_text=symptoms_text,
                    age=age,
                    gender=gender,
                    duration=duration,
                    additional_notes=additional_notes,
                    web_context=web_context,
                    language=language
                )

            prompt = GeminiService.build_combined_prompt(
                symptoms_text=symptoms_text,
                image_descriptions=image_descriptions,
                age=age,
                gender=gender,
                duration=duration,
                additional_notes=additional_notes,
                web_context=web_context
            )

            # Add language instruction
            language_instruction = GeminiService.get_language_instruction(language)
            prompt = f"{language_instruction}\n\n{prompt}"

            model = genai.GenerativeModel(
                model_name=GeminiService.MODEL_VISION,
                generation_config={
                    'temperature': GeminiService.DEFAULT_TEMPERATURE,
                    'max_output_tokens': GeminiService.DEFAULT_MAX_TOKENS
                },
                safety_settings=GeminiService.SAFETY_SETTINGS
            )

            content = [prompt] + pil_images
            response = model.generate_content(content)

            if not response or not response.text:
                return {
                    'success': False,
                    'error': 'Empty response from Gemini'
                }

            parsed_data = GeminiService.parse_response(response.text)

            if not parsed_data:
                return {
                    'success': False,
                    'error': 'Failed to parse AI response'
                }

            return {
                'success': True,
                'data': parsed_data,
                'raw_response': response.text
            }

        except Exception as e:
            print(f"[ANALYZE COMBINED ERROR] {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


    # ============================================
    # CHAT RESPONSE (WITH LANGUAGE SUPPORT)
    # ============================================
    @staticmethod
    def chat_response(
        prompt: str,
        temperature: float = 0.8,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Generate a chat response for follow-up questions.

        Args:
            prompt: Complete chat prompt with context
            temperature: Response creativity
            language: Response language (en/hi/bn/hinglish/benglish/auto)

        Returns:
            Response dictionary
        """

        try:
            GeminiService.initialize()

            # Add language instruction to prompt
            language_instruction = GeminiService.get_language_instruction(language)
            enhanced_prompt = f"{language_instruction}\n\n{prompt}"

            model = genai.GenerativeModel(
                model_name=GeminiService.MODEL_TEXT,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': GeminiService.CHAT_MAX_TOKENS
                },
                safety_settings=GeminiService.SAFETY_SETTINGS
            )

            response = model.generate_content(enhanced_prompt)

            if not response or not response.text:
                return {
                    'success': False,
                    'error': 'Empty response from Gemini'
                }

            return {
                'success': True,
                'content': response.text.strip(),
                'tokens_used': len(response.text.split()),
                'language': language
            }

        except Exception as e:
            print(f"[CHAT RESPONSE ERROR] {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


    # ============================================
    # BUILD TEXT PROMPT (WITH WEB CONTEXT)
    # ============================================
    @staticmethod
    def build_text_prompt(
        symptoms_text: str,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        duration: Optional[str] = None,
        additional_notes: Optional[str] = None,
        web_context: Optional[str] = None
    ) -> str:
        """Build comprehensive prompt with optional web context"""

        patient_info = []
        if age:
            patient_info.append(f"Age: {age} years")
        if gender:
            patient_info.append(f"Gender: {gender}")
        if duration:
            patient_info.append(f"Duration: {duration}")

        patient_block = "\n".join(patient_info) if patient_info else "Not provided"
        notes_block = additional_notes if additional_notes else "None"

        # Web context section
        web_section = ""
        if web_context:
            web_section = f"""

==================================================
LATEST MEDICAL RESEARCH FROM TRUSTED SOURCES
==================================================
The following information has been gathered from authoritative medical websites
including Mayo Clinic, WebMD, NHS, MedlinePlus, and other trusted sources:

{web_context}

USE THIS INFORMATION TO PROVIDE ACCURATE, EVIDENCE-BASED ANALYSIS.
Cross-reference symptoms with this current medical information.
"""

        prompt = f"""You are a senior medical doctor with 25+ years of clinical experience. You are having a detailed consultation with a patient. Provide thorough, compassionate, and medically accurate information.

IMPORTANT DISCLAIMERS:
- You are an AI assistant providing educational information
- This is NOT a medical diagnosis
- Always recommend professional medical consultation
- Be thorough, empathetic, and evidence-based

PATIENT INFORMATION:
{patient_block}

REPORTED SYMPTOMS:
{symptoms_text}

ADDITIONAL NOTES:
{notes_block}
{web_section}

==================================================
PROVIDE A COMPREHENSIVE MEDICAL CONSULTATION
==================================================

Imagine you are explaining to the patient face-to-face in a clinic.
Be detailed, clear, and caring in your explanation.
Use simple language that any person can understand.

REQUIRED SECTIONS (All must be detailed and comprehensive):

1. PROBABLE CONDITIONS (Top 3):
   For each condition provide:
   - Full medical name
   - Confidence score (0.0-1.0)
   - 3-4 sentence description explaining what this condition is,
     why you suspect it, and how it relates to the reported symptoms
   - Related medical tags

2. SEVERITY ASSESSMENT:
   Choose: Low / Medium / High / Critical
   Based on the symptoms severity, duration, and potential complications

3. DETAILED EXPLANATION (MUST be 5-7 paragraphs, 500-800 words):

   Paragraph 1 - WHAT IS THIS CONDITION:
   "Based on your symptoms, you are most likely experiencing [condition name].
   This is a [type] condition that affects [body part/system]. It occurs when
   [mechanism]. This condition is [common/uncommon] and affects approximately
   [statistics] people."

   Paragraph 2 - WHY YOU ARE EXPERIENCING THIS:
   "Given your age of [age] and the fact that you have been experiencing
   these symptoms for [duration], this suggests [reasoning]. The combination
   of [symptom 1] and [symptom 2] is characteristic of [condition] because
   [explanation of why these symptoms appear together]."

   Paragraph 3 - WHAT IS HAPPENING IN YOUR BODY:
   "When [condition] occurs, your body responds by [mechanism]. This is why
   you are feeling [symptom explanation]. The [specific symptom] happens
   because [detailed medical explanation in simple words]."

   Paragraph 4 - EXPECTED PROGRESSION:
   "If left untreated, this condition may [progression]. However, with proper
   care, most people see improvement within [timeline]. You should start
   feeling better in [specific timeframe]."

   Paragraph 5 - WHEN TO WORRY:
   "While this condition is usually [manageable/serious], you should seek
   immediate medical attention if you notice [specific warning signs].
   These could indicate [complications]."

   Paragraph 6 - RECOVERY AND OUTLOOK:
   "The good news is that [condition] typically resolves [timeline] with
   proper care. To speed up your recovery, focus on [key actions].
   Most patients recover fully within [timeframe]."

   Paragraph 7 - PREVENTION:
   "To prevent recurrence, consider [prevention strategies]. Making these
   lifestyle changes can significantly reduce your risk."

4. ROOT CAUSES (6-8 detailed causes):
   For each cause explain:
   - What the cause is
   - HOW it leads to the symptoms
   - WHY it happens in the patient's case
   - Risk factors involved
   Format: "Cause Name: Your [symptom] is likely triggered by [cause]
   because [detailed mechanism]. This is especially common in people who
   [risk factors]. When [cause mechanism], your body responds with [symptoms]."

5. DURATION AND RECOVERY TIMELINE:
   - Typical duration: Specific days/weeks
   - Recovery time: With proper treatment
   - When improvement starts: "You should notice improvement in..."
   - Detailed explanation: "During the first [X days], you may still
     experience [symptoms]. By day [X], the [symptom] should start
     reducing. Full recovery typically takes [timeframe]."

6. WARNING SIGNS (6-8 specific signs):
   When to rush to a doctor. Be very specific:
   "Seek immediate medical help if:
   - Your [symptom] becomes [specific threshold]
   - You develop [new symptom] along with [existing symptom]
   - [Specific measurable sign like temperature above 103F]"

7. HOME REMEDIES (6-8 detailed remedies):
   For each remedy provide:
   - Name: Clear descriptive name
   - Step-by-step Instructions: "Step 1: Take [ingredient] and [action].
     Step 2: [next action]. Step 3: [how to apply/consume]. Make sure to
     [important note]."
   - How often: Specific timing like "3 times daily, 30 minutes after meals,
     for 5-7 days"
   - Why it works: "This remedy helps because [scientific/medical reason].
     The [ingredient] contains [property] which [mechanism of action].
     Clinical studies have shown that [evidence]."

8. DIET RECOMMENDATIONS:
   Foods to eat (8-10 items):
   - "Warm chicken soup: Rich in [nutrients], helps [benefit]. The warm
     broth soothes [symptom] and provides [benefit]."
   Foods to avoid (6-8 items):
   - "Cold beverages: These can worsen [symptom] because [reason].
     Cold drinks cause [mechanism] which aggravates [condition]."
   Hydration: Detailed advice with specific amounts
   Meal pattern: Specific eating schedule with reasoning

9. LIFESTYLE CHANGES:
   Activities to do (5-7 items):
   - "Light walking for 15-20 minutes: Helps improve [benefit].
     Walk in the morning when [reason]. This promotes [mechanism]."
   Activities to avoid (5-7 items):
   - "Heavy exercise: Avoid because [reason]. Your body needs
     [explanation] during recovery."
   Sleep: "Sleep 8-9 hours. Keep your room cool (around 68-72F).
   Elevate your head slightly if [condition specific advice]."
   Exercise: Specific plan with do's and don'ts

10. PRECAUTIONS:
    DO's (8-10 specific actionable items):
    - "Monitor your temperature every 4-6 hours"
    - "Keep a symptom diary to track changes"
    DON'Ts (6-8 items):
    - "Do not take antibiotics without prescription because [reason]"
    - "Avoid [specific thing] as it can [consequence]"

11. FREQUENTLY ASKED QUESTIONS (6-8 Q&A):
    Each answer must be 4-6 sentences and address the question thoroughly.

    Q: "Is [condition] contagious?"
    A: "Based on your condition, [detailed answer]. The [pathogen/cause]
    spreads through [mechanism]. To protect others, you should [precautions].
    The contagious period typically lasts [duration]. After [timeframe],
    you are usually no longer infectious."

    Q: "Can I continue working/studying?"
    A: "[Detailed practical advice based on severity]"

    Q: "What over-the-counter medications can help?"
    A: "[Specific medication names with dosages and warnings]"

    Q: "How long until I feel completely better?"
    A: "[Detailed recovery timeline with milestones]"

    Q: "Should I be worried about complications?"
    A: "[Honest assessment of risks with reassurance]"

    Q: "What should I tell my doctor during the visit?"
    A: "[List of important things to mention to the doctor]"

12. SPECIALIST TYPE:
    Choose the most appropriate specialist and explain why.

RESPONSE FORMAT (Strict JSON only):

{{
    "probable_diseases": [
        {{
            "name": "Specific Condition Name",
            "confidence": 0.85,
            "description": "Detailed 3-4 sentence description explaining what this condition is and why the patient's symptoms match",
            "tags": ["specific-tag-1", "specific-tag-2"]
        }}
    ],
    "severity": "Medium",
    "description": "2-3 sentence brief overview that summarizes the key finding",
    "detailed_explanation": "Write 5-7 detailed paragraphs (500-800 words) as described above. Address the patient directly using 'you' and 'your'. Make it feel like a real doctor consultation. Separate paragraphs with double newlines.",
    "causes": [
        "Cause Name: Your [symptom] is likely triggered by [detailed cause explanation with mechanism and risk factors]. This happens because [scientific reasoning].",
        "Another Cause: Detailed explanation..."
    ],
    "duration_info": {{
        "typical_duration": "5-7 days with treatment",
        "recovery_time": "Full recovery in 1-2 weeks",
        "improvement_expected": "Noticeable improvement within 2-3 days",
        "details": "During the first 2-3 days, you may still feel [symptoms]. By day 4-5, [improvement details]. Most patients report feeling significantly better by the end of the first week."
    }},
    "warning_signs": [
        "Seek immediate help if your fever exceeds 103F (39.4C) and does not respond to medication within 2 hours",
        "Rush to emergency if you experience difficulty breathing or chest tightness",
        "Contact your doctor if symptoms worsen after 3 days of home treatment"
    ],
    "home_remedies": [
        {{
            "name": "Specific Remedy Name",
            "instructions": "Step 1: [detailed]. Step 2: [detailed]. Step 3: [detailed]. Step 4: [how to use]. Important: [safety note].",
            "frequency": "3 times daily, 30 minutes after meals, for 5-7 days",
            "benefits": "This remedy works because [scientific reason]. The [active ingredient] has [property] that helps [mechanism]. Studies show [evidence]. You should feel relief within [timeframe] of starting this remedy."
        }}
    ],
    "diet_recommendations": {{
        "foods_to_eat": [
            "Warm chicken soup: Rich in protein and electrolytes. The warm broth helps soothe inflammation and provides hydration. Contains cysteine which helps thin mucus.",
            "Ginger tea with honey: Ginger has anti-inflammatory properties. Honey coats the throat and reduces irritation. Drink warm, not hot."
        ],
        "foods_to_avoid": [
            "Cold beverages and ice cream: Cold items can worsen throat inflammation and increase mucus production. The sudden temperature change irritates the throat lining.",
            "Spicy foods: Capsaicin in spicy foods can irritate the already inflamed throat and stomach lining, worsening discomfort."
        ],
        "hydration": "Drink at least 10-12 glasses of warm water throughout the day. Add a pinch of salt and sugar to water for better absorption. Warm fluids help thin mucus and prevent dehydration caused by fever.",
        "meal_pattern": "Eat 5-6 small meals instead of 3 large ones. This is easier on your digestive system during illness. Have your last meal at least 2 hours before sleeping."
    }},
    "lifestyle_changes": {{
        "activities_to_do": [
            "Rest in a well-ventilated room with moderate temperature (68-72F). Keep humidity levels comfortable. This helps your body focus energy on fighting the illness.",
            "Light stretching for 5-10 minutes in the morning to prevent body stiffness. Gentle neck rolls and shoulder shrugs can help relieve tension headache."
        ],
        "activities_to_avoid": [
            "Intense exercise or gym workouts: Your body needs all its energy for recovery. Exercise increases heart rate and body temperature, which can worsen fever and dehydration.",
            "Late night screen time: Blue light from phones/computers disrupts sleep quality. Poor sleep slows down recovery. Stop screens 1 hour before bed."
        ],
        "sleep_recommendations": "Sleep 8-9 hours per night. Elevate your head with an extra pillow if you have nasal congestion. Keep your room dark, cool (65-68F), and quiet. Avoid caffeine after 2 PM.",
        "exercise": "For the first 3 days, complete rest is recommended. From day 4-5, start with 10-minute gentle walks. Gradually increase activity as symptoms improve. Resume normal exercise only after all symptoms have resolved for 24 hours."
    }},
    "precautions": {{
        "dos": [
            "Monitor your body temperature every 4-6 hours and maintain a record",
            "Wash hands frequently for at least 20 seconds with soap and water",
            "Keep yourself isolated if symptoms suggest a contagious condition",
            "Stay well-hydrated - keep a water bottle nearby at all times",
            "Take medications exactly as directed - do not skip doses",
            "Ventilate your room by opening windows for 15-20 minutes daily",
            "Use a humidifier if the air is dry to ease breathing",
            "Keep a symptom diary to share with your doctor"
        ],
        "donts": [
            "Do not self-prescribe antibiotics - they only work for bacterial infections and incorrect use creates resistance",
            "Avoid alcohol completely as it dehydrates your body and interferes with immune function",
            "Do not ignore worsening symptoms - seek help if things get worse after 48 hours",
            "Avoid smoking or being around smokers - smoke irritates airways and slows healing",
            "Do not share utensils, towels, or personal items to prevent spreading infection",
            "Avoid very hot or very cold foods - stick to warm, comfortable temperatures"
        ]
    }},
    "faqs": [
        {{
            "question": "Is this condition contagious and should I isolate?",
            "answer": "Based on your symptoms of [symptoms], [detailed contagion assessment]. The typical contagious period is [duration]. During this time, maintain [specific distance/precautions]. You can resume normal social contact after [specific milestone]. To protect family members, [specific advice]."
        }},
        {{
            "question": "Can I take paracetamol or ibuprofen for the pain?",
            "answer": "Yes, for your condition, [specific medication advice]. Take [dosage] every [hours]. Do not exceed [maximum daily dose]. Take it with food to protect your stomach. If you are taking any other medications, check with your pharmacist for interactions. Avoid [specific medication] if you have [condition]."
        }},
        {{
            "question": "When should I visit a doctor in person?",
            "answer": "Based on the current severity assessment of [severity], [specific advice]. You should definitely visit a doctor if [specific conditions]. Prepare for your visit by [what to bring/note]. The doctor may want to [possible tests/examinations]."
        }},
        {{
            "question": "How long should I take off from work or school?",
            "answer": "Given the severity and nature of your condition, [specific rest period]. During this time, [what activities are okay]. You can return to work/school when [specific milestones]. If your work involves [physical/desk], adjust by [specific modifications]."
        }},
        {{
            "question": "Will this condition come back? How can I prevent it?",
            "answer": "Recurrence depends on [factors]. To minimize the risk, [specific prevention steps]. Strengthening your immune system through [specific actions] can help. Consider [long-term lifestyle changes]. If it recurs more than [frequency], consult a specialist for [further evaluation]."
        }},
        {{
            "question": "Are there any complications I should watch for?",
            "answer": "While [condition] usually resolves without complications, in rare cases it can lead to [possible complications]. Watch for [specific signs of complications]. These are more likely if [risk factors]. The chance of complications is [low/moderate] for your case because [reasoning]."
        }}
    ],
    "specialist_type": "General Physician",
    "additional_info": "Based on the overall assessment, [personalized advice]. Remember that [reassuring statement]. If you have any more questions, feel free to ask."
}}

CRITICAL INSTRUCTIONS:
1. Address the patient directly using 'you' and 'your'
2. Write as if you are a caring doctor talking to the patient
3. Every section must have REAL, DETAILED medical information
4. Do NOT use placeholder text - provide actual medical content
5. Home remedies must have REAL step-by-step instructions
6. Diet items must explain WHY each food helps or harms
7. FAQs must give PRACTICAL, ACTIONABLE answers
8. Be empathetic, clear, and thorough
9. Use simple language that anyone can understand
10. Provide ONLY JSON response without markdown formatting"""

        return prompt


    # ============================================
    # BUILD IMAGE PROMPT (WITH WEB CONTEXT)
    # ============================================
    @staticmethod
    def build_image_prompt(
        image_type: str = 'other',
        symptoms_context: Optional[str] = None,
        web_context: Optional[str] = None
    ) -> str:
        """Build detailed prompt for image-based analysis"""

        type_specific_guidance = {
            'skin': 'Focus on: skin color, texture, lesions, rashes, swelling, discoloration, spots, wounds, scaling, blistering',
            'eye': 'Focus on: redness, swelling, discharge, pupil condition, conjunctiva, eyelid issues, vision-related signs',
            'throat': 'Focus on: redness severity, swelling, white spots, tonsil condition, ulcers, discoloration',
            'other': 'Provide detailed general medical observation of the visible condition'
        }

        guidance = type_specific_guidance.get(image_type, type_specific_guidance['other'])
        context_block = symptoms_context if symptoms_context else "No additional symptoms provided"

        web_section = ""
        if web_context:
            web_section = f"""

==================================================
MEDICAL RESEARCH FROM TRUSTED SOURCES
==================================================
{web_context}

Use this information to enhance your visual analysis.
"""

        prompt = f"""You are an expert medical AI analyzing a medical image to provide COMPREHENSIVE, DETAILED educational information.

CRITICAL DISCLAIMERS:
- You are NOT a doctor and this is NOT a medical diagnosis
- Provide EXTENSIVE educational information
- Always recommend professional medical consultation

IMAGE TYPE: {image_type}

ANALYSIS GUIDANCE:
{guidance}

ADDITIONAL CONTEXT FROM PATIENT:
{context_block}
{web_section}

PROVIDE DETAILED COMPREHENSIVE ANALYSIS with same JSON structure as text analysis.
Include all sections: probable_diseases, severity, description, detailed_explanation,
causes, duration_info, warning_signs, home_remedies, diet_recommendations,
lifestyle_changes, precautions, faqs, specialist_type, visual_findings, additional_info.

Provide ONLY JSON without markdown."""

        return prompt


    # ============================================
    # BUILD COMBINED PROMPT
    # ============================================
    @staticmethod
    def build_combined_prompt(
        symptoms_text: str,
        image_descriptions: List[str],
        age: Optional[int] = None,
        gender: Optional[str] = None,
        duration: Optional[str] = None,
        additional_notes: Optional[str] = None,
        web_context: Optional[str] = None
    ) -> str:
        """Build comprehensive prompt for combined text and image analysis"""

        patient_info = []
        if age:
            patient_info.append(f"Age: {age} years")
        if gender:
            patient_info.append(f"Gender: {gender}")
        if duration:
            patient_info.append(f"Duration: {duration}")

        patient_block = "\n".join(patient_info) if patient_info else "Not provided"
        images_block = "\n".join(image_descriptions) if image_descriptions else "No images"
        notes_block = additional_notes if additional_notes else "None"

        web_section = ""
        if web_context:
            web_section = f"""

==================================================
MEDICAL RESEARCH FROM TRUSTED SOURCES
==================================================
{web_context}

Use this information for evidence-based analysis.
"""

        prompt = f"""You are an expert medical AI analyzing both symptoms text AND medical images.

CRITICAL DISCLAIMERS:
- You are NOT a doctor and this is NOT a medical diagnosis
- Provide EXTENSIVE detailed educational information

PATIENT INFORMATION:
{patient_block}

REPORTED SYMPTOMS:
{symptoms_text}

ADDITIONAL NOTES:
{notes_block}

ATTACHED IMAGES:
{images_block}
{web_section}

Combine symptom descriptions with visual evidence and web research for THOROUGH analysis.
Provide same comprehensive JSON structure with all sections.

Provide ONLY JSON without markdown."""

        return prompt


    # ============================================
    # PARSE GEMINI RESPONSE
    # ============================================
    @staticmethod
    def parse_response(response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Gemini AI response into structured data."""

        if not response_text:
            return None

        try:
            cleaned_text = response_text.strip()
            cleaned_text = re.sub(r'^```json\s*', '', cleaned_text)
            cleaned_text = re.sub(r'^```\s*', '', cleaned_text)
            cleaned_text = re.sub(r'\s*```$', '', cleaned_text)

            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)

            if json_match:
                cleaned_text = json_match.group(0)

            parsed = json.loads(cleaned_text)
            normalized = GeminiService.normalize_response(parsed)

            return normalized

        except json.JSONDecodeError as e:
            print(f"[PARSE JSON ERROR] {str(e)}")
            return GeminiService.fallback_parse(response_text)

        except Exception as e:
            print(f"[PARSE ERROR] {str(e)}")
            return None


    # ============================================
    # NORMALIZE RESPONSE
    # ============================================
    @staticmethod
    def normalize_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate response structure."""

        normalized = {
            'probable_diseases': [],
            'severity': 'Low',
            'description': '',
            'detailed_explanation': '',
            'causes': [],
            'duration_info': {},
            'warning_signs': [],
            'home_remedies': [],
            'diet_recommendations': {},
            'lifestyle_changes': {},
            'precautions': {
                'dos': [],
                'donts': []
            },
            'faqs': [],
            'specialist_type': 'General Physician',
            'visual_findings': '',
            'text_findings': '',
            'additional_info': ''
        }

        # Probable diseases
        diseases = data.get('probable_diseases', [])
        if isinstance(diseases, list):
            for disease in diseases[:3]:
                if isinstance(disease, dict):
                    normalized_disease = {
                        'name': str(disease.get('name', 'Unknown')),
                        'confidence': float(disease.get('confidence', 0.5)),
                        'description': str(disease.get('description', '')),
                        'tags': disease.get('tags', []) if isinstance(disease.get('tags'), list) else []
                    }

                    if normalized_disease['confidence'] > 1:
                        normalized_disease['confidence'] = normalized_disease['confidence'] / 100
                    normalized_disease['confidence'] = max(0.0, min(1.0, normalized_disease['confidence']))

                    normalized['probable_diseases'].append(normalized_disease)

        # Severity
        severity = str(data.get('severity', 'Low')).strip().capitalize()
        if severity in ['Low', 'Medium', 'High', 'Critical']:
            normalized['severity'] = severity

        # Basic fields
        normalized['description'] = str(data.get('description', ''))
        normalized['detailed_explanation'] = str(data.get('detailed_explanation', ''))
        normalized['additional_info'] = str(data.get('additional_info', ''))
        normalized['visual_findings'] = str(data.get('visual_findings', ''))
        normalized['text_findings'] = str(data.get('text_findings', ''))

        # Causes
        causes = data.get('causes', [])
        if isinstance(causes, list):
            normalized['causes'] = [str(c) for c in causes][:10]

        # Duration info
        duration = data.get('duration_info', {})
        if isinstance(duration, dict):
            normalized['duration_info'] = {
                'typical_duration': str(duration.get('typical_duration', '')),
                'recovery_time': str(duration.get('recovery_time', '')),
                'improvement_expected': str(duration.get('improvement_expected', '')),
                'details': str(duration.get('details', ''))
            }

        # Warning signs
        warnings = data.get('warning_signs', [])
        if isinstance(warnings, list):
            normalized['warning_signs'] = [str(w) for w in warnings][:10]

        # Home remedies
        remedies = data.get('home_remedies', [])
        if isinstance(remedies, list):
            for remedy in remedies[:8]:
                if isinstance(remedy, dict):
                    normalized['home_remedies'].append({
                        'name': str(remedy.get('name', 'Remedy')),
                        'instructions': str(remedy.get('instructions', '')),
                        'frequency': str(remedy.get('frequency', '')),
                        'benefits': str(remedy.get('benefits', ''))
                    })
                elif isinstance(remedy, str):
                    normalized['home_remedies'].append({
                        'name': 'Remedy',
                        'instructions': remedy,
                        'frequency': '',
                        'benefits': ''
                    })

        # Diet recommendations
        diet = data.get('diet_recommendations', {})
        if isinstance(diet, dict):
            normalized['diet_recommendations'] = {
                'foods_to_eat': [str(f) for f in (diet.get('foods_to_eat', []) or [])][:12],
                'foods_to_avoid': [str(f) for f in (diet.get('foods_to_avoid', []) or [])][:12],
                'hydration': str(diet.get('hydration', '')),
                'meal_pattern': str(diet.get('meal_pattern', ''))
            }

        # Lifestyle changes
        lifestyle = data.get('lifestyle_changes', {})
        if isinstance(lifestyle, dict):
            normalized['lifestyle_changes'] = {
                'activities_to_do': [str(a) for a in (lifestyle.get('activities_to_do', []) or [])][:10],
                'activities_to_avoid': [str(a) for a in (lifestyle.get('activities_to_avoid', []) or [])][:10],
                'sleep_recommendations': str(lifestyle.get('sleep_recommendations', '')),
                'exercise': str(lifestyle.get('exercise', ''))
            }

        # Precautions
        precautions = data.get('precautions', {})
        if isinstance(precautions, dict):
            dos = precautions.get('dos', [])
            donts = precautions.get('donts', [])

            if isinstance(dos, list):
                normalized['precautions']['dos'] = [str(d) for d in dos][:12]

            if isinstance(donts, list):
                normalized['precautions']['donts'] = [str(d) for d in donts][:12]

        # FAQs
        faqs = data.get('faqs', [])
        if isinstance(faqs, list):
            for faq in faqs[:10]:
                if isinstance(faq, dict):
                    normalized['faqs'].append({
                        'question': str(faq.get('question', '')),
                        'answer': str(faq.get('answer', ''))
                    })

        # Specialist type
        specialist = str(data.get('specialist_type', 'General Physician')).strip()
        valid_specialists = [
            'General Physician', 'Dermatologist', 'Ophthalmologist',
            'ENT Specialist', 'Neurologist', 'Cardiologist',
            'Orthopedist', 'Gastroenterologist', 'Pulmonologist',
            'Psychiatrist', 'Pediatrician', 'Gynecologist'
        ]

        if specialist in valid_specialists:
            normalized['specialist_type'] = specialist
        else:
            for valid_spec in valid_specialists:
                if specialist.lower() in valid_spec.lower():
                    normalized['specialist_type'] = valid_spec
                    break

        # Ensure at least one disease
        if not normalized['probable_diseases']:
            normalized['probable_diseases'].append({
                'name': 'Unable to determine',
                'confidence': 0.3,
                'description': 'Insufficient information for accurate analysis',
                'tags': []
            })

        # Default precautions
        if not normalized['precautions']['dos']:
            normalized['precautions']['dos'] = [
                'Consult a healthcare professional',
                'Monitor your symptoms',
                'Stay hydrated',
                'Get adequate rest'
            ]

        if not normalized['precautions']['donts']:
            normalized['precautions']['donts'] = [
                'Do not self-medicate',
                'Avoid ignoring worsening symptoms',
                'Do not delay seeking medical help'
            ]

        return normalized


    # ============================================
    # FALLBACK PARSER
    # ============================================
    @staticmethod
    def fallback_parse(response_text: str) -> Dict[str, Any]:
        """Fallback parser when JSON parsing fails."""

        return {
            'probable_diseases': [
                {
                    'name': 'Analysis Available',
                    'confidence': 0.5,
                    'description': response_text[:500] if response_text else 'No response',
                    'tags': []
                }
            ],
            'severity': 'Low',
            'description': 'AI analysis could not be properly structured.',
            'detailed_explanation': '',
            'causes': [],
            'duration_info': {},
            'warning_signs': [],
            'home_remedies': [],
            'diet_recommendations': {},
            'lifestyle_changes': {},
            'precautions': {
                'dos': ['Consult a qualified doctor', 'Monitor symptoms'],
                'donts': ['Do not rely solely on AI analysis']
            },
            'faqs': [],
            'specialist_type': 'General Physician',
            'additional_info': 'AI response parsing failed.'
        }


    # ============================================
    # HEALTH CHECK
    # ============================================
    @staticmethod
    def check_api_health() -> Dict[str, Any]:
        """Check if Gemini API is accessible."""

        try:
            GeminiService.initialize()
            model = genai.GenerativeModel(GeminiService.MODEL_TEXT)
            response = model.generate_content("Say 'OK' if you can read this.")

            if response and response.text:
                return {
                    'success': True,
                    'status': 'operational',
                    'model': GeminiService.MODEL_TEXT,
                    'response_received': True
                }

            return {
                'success': False,
                'status': 'no_response',
                'error': 'No response from API'
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }


    # ============================================
    # GET MODEL INFO
    # ============================================
    @staticmethod
    def get_model_info() -> Dict[str, Any]:
        """Get information about configured models."""

        return {
            'text_model': GeminiService.MODEL_TEXT,
            'vision_model': GeminiService.MODEL_VISION,
            'temperature': GeminiService.DEFAULT_TEMPERATURE,
            'max_tokens': GeminiService.DEFAULT_MAX_TOKENS,
            'chat_max_tokens': GeminiService.CHAT_MAX_TOKENS,
            'timeout_seconds': GeminiService.DEFAULT_TIMEOUT,
            'api_configured': bool(os.getenv('GEMINI_API_KEY'))
        }