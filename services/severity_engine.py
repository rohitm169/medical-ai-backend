"""
============================================
SEVERITY ENGINE
============================================
Calculates final severity level by combining
AI predictions with keyword analysis, age factors,
and emergency detection.
"""

from typing import List, Dict, Any, Optional


# ============================================
# SEVERITY ENGINE CLASS
# ============================================
class SeverityEngine:
    """Service class for severity calculation and classification"""

    # ============================================
    # SEVERITY LEVELS
    # ============================================
    SEVERITY_LEVELS = ['Low', 'Medium', 'High', 'Critical']

    SEVERITY_SCORES = {
        'Low': 1,
        'Medium': 2,
        'High': 3,
        'Critical': 4
    }

    SCORE_TO_SEVERITY = {
        1: 'Low',
        2: 'Medium',
        3: 'High',
        4: 'Critical'
    }


    # ============================================
    # EMERGENCY KEYWORDS (Critical)
    # ============================================
    CRITICAL_KEYWORDS = [
        # Cardiac
        'chest pain',
        'heart attack',
        'cardiac arrest',
        'severe chest pressure',

        # Breathing
        'cannot breathe',
        "can't breathe",
        'difficulty breathing',
        'shortness of breath severe',
        'choking',
        'suffocating',

        # Bleeding
        'severe bleeding',
        'heavy bleeding',
        'blood loss',
        'hemorrhage',

        # Neurological
        'unconscious',
        'unresponsive',
        'stroke',
        'seizure',
        'paralysis',
        'sudden weakness',
        'severe head injury',
        'loss of consciousness',
        'fainting repeatedly',

        # Mental health
        'suicidal',
        'suicide',
        'self harm',
        'want to die',
        'kill myself',

        # Severe symptoms
        'overdose',
        'poisoning',
        'severe burn',
        'anaphylaxis',
        'anaphylactic',
        'severe allergic reaction',
        'throat swelling',
        'tongue swelling',

        # Emergency conditions
        'high fever above 104',
        'severe dehydration',
        'extreme pain',
        'unbearable pain'
    ]


    # ============================================
    # HIGH SEVERITY KEYWORDS
    # ============================================
    HIGH_KEYWORDS = [
        'severe pain',
        'intense pain',
        'high fever',
        'persistent vomiting',
        'blood in stool',
        'blood in urine',
        'blood in vomit',
        'severe headache',
        'sudden vision loss',
        'sudden hearing loss',
        'severe abdominal pain',
        'severe back pain',
        'broken bone',
        'fracture',
        'deep wound',
        'infected wound',
        'pus',
        'severe rash',
        'spreading rash',
        'severe diarrhea',
        'dehydrated',
        'cannot eat',
        'cannot drink',
        'extreme fatigue',
        'rapid heartbeat',
        'irregular heartbeat'
    ]


    # ============================================
    # MEDIUM SEVERITY KEYWORDS
    # ============================================
    MEDIUM_KEYWORDS = [
        'fever',
        'persistent cough',
        'chronic pain',
        'recurring',
        'worsening',
        'getting worse',
        'spreading',
        'swelling',
        'inflammation',
        'rash',
        'infection',
        'discharge',
        'stiffness',
        'numbness',
        'tingling',
        'dizziness',
        'nausea persistent',
        'weight loss unexplained',
        'fatigue persistent',
        'joint pain',
        'muscle pain severe'
    ]


    # ============================================
    # LOW SEVERITY KEYWORDS
    # ============================================
    LOW_KEYWORDS = [
        'mild',
        'slight',
        'occasional',
        'minor',
        'small',
        'common cold',
        'sneezing',
        'runny nose',
        'mild headache',
        'tired',
        'minor cut',
        'small bruise',
        'mild rash',
        'itchy',
        'sore throat mild'
    ]


    # ============================================
    # AGE-BASED RISK FACTORS
    # ============================================
    HIGH_RISK_AGE_GROUPS = {
        'infant': (0, 2),
        'young_child': (3, 5),
        'elderly': (65, 120),
        'very_elderly': (80, 120)
    }


    # ============================================
    # CRITICAL DISEASES
    # ============================================
    CRITICAL_DISEASES = [
        'heart attack',
        'myocardial infarction',
        'stroke',
        'cerebrovascular accident',
        'pulmonary embolism',
        'sepsis',
        'meningitis',
        'anaphylaxis',
        'cardiac arrest',
        'aortic dissection',
        'acute appendicitis',
        'severe pneumonia',
        'diabetic ketoacidosis',
        'acute kidney failure',
        'liver failure'
    ]


    # ============================================
    # MAIN CALCULATION METHOD
    # ============================================
    @staticmethod
    def calculate_severity(
        ai_severity: str,
        symptoms_text: str = '',
        age: Optional[int] = None,
        probable_diseases: List[Dict[str, Any]] = None,
        gender: Optional[str] = None
    ) -> str:
        """
        Calculate final severity by combining multiple factors.

        Args:
            ai_severity: Severity from AI analysis
            symptoms_text: User's symptom description
            age: Patient age
            probable_diseases: List of probable diseases from AI
            gender: Patient gender

        Returns:
            str: Final severity level (Low/Medium/High/Critical)
        """

        try:
            # Start with AI severity
            base_score = SeverityEngine.SEVERITY_SCORES.get(ai_severity, 1)

            # Check for emergency keywords (CRITICAL override)
            if SeverityEngine.check_critical_keywords(symptoms_text):
                return 'Critical'

            # Check for critical diseases
            if probable_diseases:
                if SeverityEngine.check_critical_diseases(probable_diseases):
                    return 'Critical'

            # Check keyword-based severity
            keyword_score = SeverityEngine.calculate_keyword_score(symptoms_text)

            # Apply age factor
            age_modifier = SeverityEngine.get_age_modifier(age)

            # Calculate confidence factor
            confidence_modifier = SeverityEngine.get_confidence_modifier(probable_diseases)

            # Combine scores (weighted average)
            final_score = max(
                base_score,
                keyword_score
            )

            # Apply modifiers
            final_score += age_modifier
            final_score += confidence_modifier

            # Round and clamp
            final_score = round(final_score)
            final_score = max(1, min(4, final_score))

            return SeverityEngine.SCORE_TO_SEVERITY.get(final_score, 'Low')

        except Exception as e:
            print(f"[SEVERITY CALC ERROR] {str(e)}")
            return ai_severity if ai_severity in SeverityEngine.SEVERITY_LEVELS else 'Low'


    # ============================================
    # CHECK CRITICAL KEYWORDS
    # ============================================
    @staticmethod
    def check_critical_keywords(symptoms_text: str) -> bool:
        """
        Check if symptoms contain critical emergency keywords.

        Args:
            symptoms_text: Symptom description

        Returns:
            bool: True if critical keywords found
        """

        if not symptoms_text:
            return False

        text_lower = symptoms_text.lower()

        for keyword in SeverityEngine.CRITICAL_KEYWORDS:
            if keyword.lower() in text_lower:
                print(f"[CRITICAL KEYWORD FOUND] {keyword}")
                return True

        return False


    # ============================================
    # CHECK CRITICAL DISEASES
    # ============================================
    @staticmethod
    def check_critical_diseases(probable_diseases: List[Dict[str, Any]]) -> bool:
        """
        Check if any probable disease is in critical list.

        Args:
            probable_diseases: List of disease objects

        Returns:
            bool: True if critical disease found
        """

        if not probable_diseases:
            return False

        for disease in probable_diseases:
            if not isinstance(disease, dict):
                continue

            disease_name = disease.get('name', '').lower()
            confidence = disease.get('confidence', 0)

            # Only consider high confidence predictions
            if confidence < 0.5:
                continue

            for critical in SeverityEngine.CRITICAL_DISEASES:
                if critical.lower() in disease_name:
                    print(f"[CRITICAL DISEASE FOUND] {disease_name}")
                    return True

        return False


    # ============================================
    # CALCULATE KEYWORD SCORE
    # ============================================
    @staticmethod
    def calculate_keyword_score(symptoms_text: str) -> int:
        """
        Calculate severity score based on keyword analysis.

        Args:
            symptoms_text: Symptom description

        Returns:
            int: Severity score (1-4)
        """

        if not symptoms_text:
            return 1

        text_lower = symptoms_text.lower()

        # Count matches for each severity level
        critical_count = sum(
            1 for kw in SeverityEngine.CRITICAL_KEYWORDS
            if kw.lower() in text_lower
        )

        high_count = sum(
            1 for kw in SeverityEngine.HIGH_KEYWORDS
            if kw.lower() in text_lower
        )

        medium_count = sum(
            1 for kw in SeverityEngine.MEDIUM_KEYWORDS
            if kw.lower() in text_lower
        )

        low_count = sum(
            1 for kw in SeverityEngine.LOW_KEYWORDS
            if kw.lower() in text_lower
        )

        # Determine score based on highest match
        if critical_count > 0:
            return 4
        elif high_count >= 1:
            return 3
        elif medium_count >= 2:
            return 3
        elif medium_count >= 1:
            return 2
        elif low_count >= 1:
            return 1
        else:
            return 1


    # ============================================
    # AGE MODIFIER
    # ============================================
    @staticmethod
    def get_age_modifier(age: Optional[int]) -> float:
        """
        Get severity modifier based on age.

        Higher risk for very young and elderly.

        Args:
            age: Patient age

        Returns:
            float: Score modifier
        """

        if age is None:
            return 0.0

        try:
            age = int(age)

            # Infants (0-2 years) - higher risk
            if age <= 2:
                return 1.0

            # Young children (3-5 years)
            if age <= 5:
                return 0.5

            # Very elderly (80+) - higher risk
            if age >= 80:
                return 1.0

            # Elderly (65+)
            if age >= 65:
                return 0.5

            # Adults - no modifier
            return 0.0

        except (ValueError, TypeError):
            return 0.0


    # ============================================
    # CONFIDENCE MODIFIER
    # ============================================
    @staticmethod
    def get_confidence_modifier(
        probable_diseases: List[Dict[str, Any]]
    ) -> float:
        """
        Get severity modifier based on AI confidence.

        Lower confidence may indicate need for medical consultation.

        Args:
            probable_diseases: List of diseases with confidence

        Returns:
            float: Score modifier
        """

        if not probable_diseases:
            return 0.5

        try:
            # Get highest confidence
            top_confidence = max(
                d.get('confidence', 0)
                for d in probable_diseases
                if isinstance(d, dict)
            )

            # Very low confidence - recommend doctor consultation
            if top_confidence < 0.4:
                return 0.5

            # Low confidence
            if top_confidence < 0.6:
                return 0.3

            # No modifier for high confidence
            return 0.0

        except Exception:
            return 0.0


    # ============================================
    # GET URGENCY LEVEL
    # ============================================
    @staticmethod
    def get_urgency_level(severity: str) -> str:
        """
        Get urgency level from severity.

        Args:
            severity: Severity level

        Returns:
            str: Urgency level (routine/soon/urgent/emergency)
        """

        urgency_map = {
            'Low': 'routine',
            'Medium': 'soon',
            'High': 'urgent',
            'Critical': 'emergency'
        }

        return urgency_map.get(severity, 'routine')


    # ============================================
    # GET SEVERITY ACTION
    # ============================================
    @staticmethod
    def get_severity_action(severity: str) -> Dict[str, str]:
        """
        Get recommended action based on severity.

        Args:
            severity: Severity level

        Returns:
            dict: Action recommendation
        """

        actions = {
            'Low': {
                'action': 'home_care',
                'title': 'Home Care Recommended',
                'description': 'Rest at home and monitor your symptoms. Consider seeing a doctor if symptoms persist for more than 3 days or worsen.',
                'timeframe': 'Monitor for 2-3 days',
                'icon': 'check-circle',
                'color': 'green'
            },
            'Medium': {
                'action': 'see_doctor_soon',
                'title': 'Doctor Visit Recommended',
                'description': 'Schedule an appointment with a doctor within the next few days. Monitor your symptoms closely and seek immediate care if they worsen.',
                'timeframe': 'Within 3-7 days',
                'icon': 'exclamation-circle',
                'color': 'yellow'
            },
            'High': {
                'action': 'see_doctor_asap',
                'title': 'Urgent Medical Attention',
                'description': 'See a doctor as soon as possible, preferably within 24-48 hours. Do not delay medical attention.',
                'timeframe': 'Within 24-48 hours',
                'icon': 'exclamation-triangle',
                'color': 'orange'
            },
            'Critical': {
                'action': 'emergency_care',
                'title': 'Seek Emergency Care Now',
                'description': 'Seek immediate medical attention. Go to the nearest emergency room or call emergency services right away.',
                'timeframe': 'Immediately',
                'icon': 'ambulance',
                'color': 'red'
            }
        }

        return actions.get(severity, actions['Low'])


    # ============================================
    # APPLY AGE FACTOR (Public Method)
    # ============================================
    @staticmethod
    def apply_age_factor(
        base_severity: str,
        age: Optional[int]
    ) -> str:
        """
        Apply age-based severity adjustment.

        Args:
            base_severity: Original severity
            age: Patient age

        Returns:
            str: Adjusted severity
        """

        if age is None or not base_severity:
            return base_severity

        base_score = SeverityEngine.SEVERITY_SCORES.get(base_severity, 1)
        age_modifier = SeverityEngine.get_age_modifier(age)

        new_score = round(base_score + age_modifier)
        new_score = max(1, min(4, new_score))

        return SeverityEngine.SCORE_TO_SEVERITY.get(new_score, base_severity)


    # ============================================
    # GET SEVERITY DETAILS
    # ============================================
    @staticmethod
    def get_severity_details(severity: str) -> Dict[str, Any]:
        """
        Get complete details about a severity level.

        Args:
            severity: Severity level

        Returns:
            dict: Severity details
        """

        details = {
            'Low': {
                'level': 'Low',
                'score': 1,
                'urgency': 'routine',
                'color': '#10b981',
                'color_name': 'green',
                'description': 'Minor symptoms that can typically be managed at home',
                'response_time': 'Monitor for several days',
                'examples': [
                    'Common cold',
                    'Minor headache',
                    'Mild rash',
                    'Small cut or bruise'
                ]
            },
            'Medium': {
                'level': 'Medium',
                'score': 2,
                'urgency': 'soon',
                'color': '#f59e0b',
                'color_name': 'yellow',
                'description': 'Symptoms that warrant medical attention within a week',
                'response_time': '3-7 days',
                'examples': [
                    'Persistent fever',
                    'Recurring symptoms',
                    'Spreading skin condition',
                    'Persistent cough'
                ]
            },
            'High': {
                'level': 'High',
                'score': 3,
                'urgency': 'urgent',
                'color': '#ef4444',
                'color_name': 'orange',
                'description': 'Serious symptoms requiring prompt medical care',
                'response_time': '24-48 hours',
                'examples': [
                    'High fever with body pain',
                    'Severe pain',
                    'Infected wounds',
                    'Vision problems'
                ]
            },
            'Critical': {
                'level': 'Critical',
                'score': 4,
                'urgency': 'emergency',
                'color': '#dc2626',
                'color_name': 'red',
                'description': 'Life-threatening symptoms requiring immediate emergency care',
                'response_time': 'Immediate',
                'examples': [
                    'Chest pain',
                    'Difficulty breathing',
                    'Severe bleeding',
                    'Loss of consciousness',
                    'Stroke symptoms'
                ]
            }
        }

        return details.get(severity, details['Low'])


    # ============================================
    # CHECK SYMPTOM COMBINATIONS
    # ============================================
    @staticmethod
    def check_symptom_combinations(symptoms_text: str) -> Dict[str, Any]:
        """
        Check for dangerous symptom combinations.

        Args:
            symptoms_text: Symptom description

        Returns:
            dict: Combination analysis
        """

        if not symptoms_text:
            return {'has_dangerous_combination': False}

        text_lower = symptoms_text.lower()

        dangerous_combinations = [
            {
                'symptoms': ['chest pain', 'shortness of breath'],
                'condition': 'Possible cardiac event',
                'severity': 'Critical'
            },
            {
                'symptoms': ['fever', 'stiff neck', 'headache'],
                'condition': 'Possible meningitis',
                'severity': 'Critical'
            },
            {
                'symptoms': ['sudden weakness', 'slurred speech'],
                'condition': 'Possible stroke',
                'severity': 'Critical'
            },
            {
                'symptoms': ['high fever', 'rash'],
                'condition': 'Possible serious infection',
                'severity': 'High'
            },
            {
                'symptoms': ['vomiting', 'severe headache'],
                'condition': 'Possible serious condition',
                'severity': 'High'
            },
            {
                'symptoms': ['blood in stool', 'abdominal pain'],
                'condition': 'Possible GI bleeding',
                'severity': 'High'
            }
        ]

        found_combinations = []

        for combo in dangerous_combinations:
            all_present = all(
                symptom.lower() in text_lower
                for symptom in combo['symptoms']
            )

            if all_present:
                found_combinations.append(combo)

        return {
            'has_dangerous_combination': len(found_combinations) > 0,
            'combinations': found_combinations,
            'count': len(found_combinations)
        }


    # ============================================
    # GET PRECAUTIONS BY SEVERITY
    # ============================================
    @staticmethod
    def get_default_precautions(severity: str) -> Dict[str, List[str]]:
        """
        Get default precautions based on severity level.

        Args:
            severity: Severity level

        Returns:
            dict: Precautions with do's and don'ts
        """

        precautions = {
            'Low': {
                'dos': [
                    'Get adequate rest',
                    'Stay hydrated - drink plenty of water',
                    'Monitor your symptoms',
                    'Eat light, nutritious meals',
                    'Practice good hygiene'
                ],
                'donts': [
                    'Do not ignore worsening symptoms',
                    'Avoid self-medication without guidance',
                    'Do not engage in strenuous activity',
                    'Avoid alcohol and smoking'
                ]
            },
            'Medium': {
                'dos': [
                    'Schedule a doctor appointment soon',
                    'Rest and avoid physical exertion',
                    'Keep a symptom diary',
                    'Stay hydrated and eat well',
                    'Take prescribed medications as directed'
                ],
                'donts': [
                    'Do not delay medical consultation',
                    'Avoid stressful activities',
                    'Do not ignore new symptoms',
                    'Avoid heavy meals',
                    'Do not stop medications without doctor advice'
                ]
            },
            'High': {
                'dos': [
                    'See a doctor within 24-48 hours',
                    'Have someone stay with you',
                    'Keep emergency contacts ready',
                    'Note all symptom changes',
                    'Take vital signs if possible'
                ],
                'donts': [
                    'Do not drive yourself if feeling unwell',
                    'Do not ignore symptom progression',
                    'Avoid being alone',
                    'Do not delay seeking care',
                    'Avoid any strenuous activity'
                ]
            },
            'Critical': {
                'dos': [
                    'Call emergency services immediately (999)',
                    'Go to the nearest emergency room',
                    'Stay calm and seated/lying down',
                    'Have someone with you',
                    'Bring list of medications and conditions'
                ],
                'donts': [
                    'Do not drive yourself - call ambulance',
                    'Do not delay seeking emergency care',
                    'Do not eat or drink (in case surgery is needed)',
                    'Do not take any medications without consultation',
                    'Do not ignore the symptoms'
                ]
            }
        }

        return precautions.get(severity, precautions['Low'])


    # ============================================
    # ESTIMATE RECOVERY TIME
    # ============================================
    @staticmethod
    def estimate_recovery_time(severity: str) -> Dict[str, str]:
        """
        Estimate typical recovery time based on severity.

        Args:
            severity: Severity level

        Returns:
            dict: Recovery time estimate
        """

        estimates = {
            'Low': {
                'minimum': '1-3 days',
                'typical': '3-7 days',
                'maximum': '1-2 weeks',
                'note': 'Most low severity conditions resolve with home care'
            },
            'Medium': {
                'minimum': '1 week',
                'typical': '2-3 weeks',
                'maximum': '1 month',
                'note': 'Recovery time varies based on treatment compliance'
            },
            'High': {
                'minimum': '2 weeks',
                'typical': '3-6 weeks',
                'maximum': '2-3 months',
                'note': 'Requires medical treatment and monitoring'
            },
            'Critical': {
                'minimum': 'Variable',
                'typical': 'Depends on condition',
                'maximum': 'Long-term',
                'note': 'Recovery depends on emergency response and treatment'
            }
        }

        return estimates.get(severity, estimates['Low'])


    # ============================================
    # FULL SEVERITY ANALYSIS
    # ============================================
    @staticmethod
    def full_analysis(
        ai_severity: str,
        symptoms_text: str = '',
        age: Optional[int] = None,
        probable_diseases: List[Dict[str, Any]] = None,
        gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform complete severity analysis.

        Args:
            ai_severity: AI-suggested severity
            symptoms_text: Symptom description
            age: Patient age
            probable_diseases: Probable diseases list
            gender: Patient gender

        Returns:
            dict: Complete analysis result
        """

        # Calculate final severity
        final_severity = SeverityEngine.calculate_severity(
            ai_severity=ai_severity,
            symptoms_text=symptoms_text,
            age=age,
            probable_diseases=probable_diseases,
            gender=gender
        )

        # Check for dangerous combinations
        combinations = SeverityEngine.check_symptom_combinations(symptoms_text)

        # Get severity details
        details = SeverityEngine.get_severity_details(final_severity)

        # Get action
        action = SeverityEngine.get_severity_action(final_severity)

        # Get urgency
        urgency = SeverityEngine.get_urgency_level(final_severity)

        # Check if was upgraded
        was_upgraded = (
            SeverityEngine.SEVERITY_SCORES.get(final_severity, 0) >
            SeverityEngine.SEVERITY_SCORES.get(ai_severity, 0)
        )

        return {
            'final_severity': final_severity,
            'ai_severity': ai_severity,
            'was_upgraded': was_upgraded,
            'urgency': urgency,
            'action': action,
            'details': details,
            'dangerous_combinations': combinations,
            'recovery_estimate': SeverityEngine.estimate_recovery_time(final_severity),
            'default_precautions': SeverityEngine.get_default_precautions(final_severity),
            'requires_emergency': final_severity == 'Critical',
            'age_factor_applied': age is not None and age <= 5 or (age is not None and age >= 65)
        }