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

        prompt = f"""You are an expert medical AI assistant providing COMPREHENSIVE, DETAILED, and EVIDENCE-BASED educational information about health conditions.

CRITICAL DISCLAIMERS:
- You are NOT a doctor and your analysis is NOT a medical diagnosis
- Provide EXTENSIVE educational information based on medical sources
- Always recommend professional medical consultation
- Be safety-focused, conservative, and thorough
- Use the provided web research to ensure accuracy

PATIENT INFORMATION:
{patient_block}

REPORTED SYMPTOMS:
{symptoms_text}

ADDITIONAL NOTES:
{notes_block}
{web_section}

==================================================
PROVIDE EXTENSIVE DETAILED ANALYSIS
==================================================

Your response must be COMPREHENSIVE with detailed explanations.
Use the web research provided to ensure medical accuracy.

REQUIREMENTS:

1. PROBABLE DISEASES (Top 3):
   - Specific medical condition names
   - Confidence scores (0.0-1.0)
   - Detailed descriptions (3-4 sentences each)
   - Medical tags/keywords

2. SEVERITY LEVEL: Low / Medium / High / Critical

3. DETAILED EXPLANATION (4-6 PARAGRAPHS, 400-600 WORDS):
   - What is this condition (definition)
   - How common it is, who gets affected
   - How it affects the body (mechanism)
   - Progression and complications
   - Recovery process
   - Prevention strategies

4. CAUSES (5-7 detailed causes):
   Each with mechanism and risk factors

5. DURATION & RECOVERY (specific timeline)

6. WARNING SIGNS (5-8 specific signs)

7. HOME REMEDIES (5-7 detailed remedies):
   Each with step-by-step instructions, frequency, and benefits

8. DIET RECOMMENDATIONS (detailed)

9. LIFESTYLE CHANGES (detailed)

10. PRECAUTIONS (do's and don'ts)

11. FAQs (6-8 comprehensive Q&A)

12. SPECIALIST TYPE

RESPONSE FORMAT (Strict JSON only):

{{
    "probable_diseases": [
        {{
            "name": "Specific Condition Name",
            "confidence": 0.85,
            "description": "Detailed 3-4 sentence description with medical accuracy",
            "tags": ["specific-tag-1", "specific-tag-2"]
        }}
    ],
    "severity": "Medium",
    "description": "Brief 2-3 sentence overview",
    "detailed_explanation": "Multiple detailed paragraphs (4-6) explaining the condition comprehensively. Include definition, prevalence, mechanism, progression, recovery, and prevention. Use information from web sources to ensure accuracy.",
    "causes": [
        "Cause 1: Detailed explanation with mechanism",
        "Cause 2: Detailed explanation",
        "Cause 3: Detailed explanation",
        "Cause 4: Detailed explanation",
        "Cause 5: Detailed explanation"
    ],
    "duration_info": {{
        "typical_duration": "Specific timeframe",
        "recovery_time": "Recovery timeline",
        "improvement_expected": "When improvement starts",
        "details": "Detailed 3-4 sentence recovery process explanation"
    }},
    "warning_signs": [
        "Specific warning sign 1 with detailed explanation",
        "Specific warning sign 2 with details",
        "Specific warning sign 3 with details",
        "Specific warning sign 4 with details",
        "Specific warning sign 5 with details"
    ],
    "home_remedies": [
        {{
            "name": "Specific Remedy Name",
            "instructions": "Step 1: Detailed first step. Step 2: Next step. Step 3: Continue with specific actions. Step 4: Final preparation.",
            "frequency": "Specific timing (e.g., 3 times daily after meals)",
            "benefits": "Detailed 2-3 sentence explanation of HOW and WHY it helps"
        }}
    ],
    "diet_recommendations": {{
        "foods_to_eat": [
            "Food 1: Why it helps - specific nutrients",
            "Food 2: Why it helps - specific benefits"
        ],
        "foods_to_avoid": [
            "Food 1: Why to avoid - specific harmful effects",
            "Food 2: Why to avoid"
        ],
        "hydration": "Detailed hydration advice",
        "meal_pattern": "Specific eating schedule"
    }},
    "lifestyle_changes": {{
        "activities_to_do": ["Activity with detailed instructions"],
        "activities_to_avoid": ["Activity with reasons"],
        "sleep_recommendations": "Detailed sleep advice",
        "exercise": "Specific exercise plan"
    }},
    "precautions": {{
        "dos": [
            "Specific actionable step 1",
            "Specific actionable step 2"
        ],
        "donts": [
            "Specific thing to avoid 1",
            "Specific thing to avoid 2"
        ]
    }},
    "faqs": [
        {{
            "question": "Is this condition contagious?",
            "answer": "Detailed 3-5 sentence answer based on medical sources"
        }}
    ],
    "specialist_type": "General Physician",
    "additional_info": "Any other important information from the web research"
}}

CRITICAL INSTRUCTIONS:
1. Use the web research provided to ensure medical accuracy
2. Provide REAL, DETAILED medical information, NOT placeholders
3. Each field must be COMPREHENSIVE and INFORMATIVE
4. Description should be LONG (multiple paragraphs)
5. Remedies should have STEP-BY-STEP detailed instructions
6. Cross-reference information from multiple sources
7. Provide ONLY JSON response without markdown
8. Be specific with measurements, timings, and frequencies"""

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