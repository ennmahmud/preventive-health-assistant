"""
Answer Normalizer
=================
Converts free-text chat answers into canonical intermediate lifestyle keys.

Used when users answer lifestyle questions in free-form chat (not via the
structured wizard). The wizard sends canonical option_keys directly.
"""

import re
from typing import Any, Dict, Optional


class AnswerNormalizer:
    """Normalizes raw natural-language answers to canonical lifestyle keys."""

    def normalize_activity(self, raw: str) -> Optional[str]:
        r = raw.lower()
        if re.search(r"very active|gym every day|daily (exercise|workout)|manual (work|labour|labor)|"
                     r"physically demanding|sport(s)? every", r):
            return "active"
        if re.search(r"moderate|3.*(week|times)|gym.*week|walk.*regular|cycling|swim|jog|run", r):
            return "moderate"
        if re.search(r"light|occasional walk|a little|some walking|walk|bit active", r):
            return "light"
        if re.search(r"sedentary|desk job|mostly sit|couch|rarely|never exercise|not active|"
                     r"don'?t exercise|no exercise|inactive", r):
            return "sedentary"
        return None

    def normalize_diet(self, raw: str) -> Optional[str]:
        r = raw.lower()
        if re.search(r"healthy|vegetables|salad|whole grain|lean protein|fruit|balanced.*diet|"
                     r"mostly.*healthy|eat (well|clean)|plant.based", r):
            return "healthy"
        if re.search(r"junk|fast food|processed|fried|lots of.*sugar|takeaway|chips|candy|"
                     r"sweets|mostly.*unhealthy|bad diet|poor diet", r):
            return "poor"
        if re.search(r"mixed|average|sometimes|okay|moderate|bit of both|could be better", r):
            return "mixed"
        return None

    def normalize_sleep(self, raw: str) -> Optional[str]:
        r = raw.lower()
        # Try to extract a number first
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)', r)
        if m:
            hrs = float(m.group(1))
            if hrs < 5:    return "under5"
            if hrs < 7:    return "5to6"
            if hrs <= 8:   return "7to8"
            return "over8"
        if re.search(r"less than 5|under 5|very little|barely sleep|4 hours", r):
            return "under5"
        if re.search(r"5.*(hour|hrs)|6.*(hour|hrs)|not enough|poor sleep|struggle.*sleep", r):
            return "5to6"
        if re.search(r"7.*(hour|hrs)|8.*(hour|hrs)|good sleep|enough sleep", r):
            return "7to8"
        if re.search(r"9|10|11|more than 8|over 8|a lot.*sleep", r):
            return "over8"
        return None

    def normalize_alcohol(self, raw: str) -> Optional[str]:
        r = raw.lower()
        if re.search(r"don'?t drink|no alcohol|none|teetotal|never drink|abstain", r):
            return "none"
        if re.search(r"occasional|once in a while|social|a glass|couple.*week|1.2.*week|"
                     r"light.*drink|rarely drink", r):
            return "light"
        if re.search(r"few times a week|3.4.*week|moderate.*drink|weekend", r):
            return "moderate"
        if re.search(r"every day|daily|heavy|a lot|binge|more than.*week|drink.*often|"
                     r"14|15|16|17|18|19|20", r):
            return "heavy"
        return None

    def normalize_stress(self, raw: str) -> Optional[int]:
        r = raw.lower()
        # Numeric "I rate my stress 4/5"
        m = re.search(r'(\d)\s*(?:out of\s*5|/\s*5)', r)
        if m:
            return max(1, min(5, int(m.group(1))))
        if re.search(r"very stressed|extremely stressed|very high stress|burn.*out|overwhelm", r):
            return 5
        if re.search(r"quite stressed|pretty stressed|high stress|stressful (job|life|work)", r):
            return 4
        if re.search(r"moderate|somewhat|average stress|a bit stressed|sometimes stressed", r):
            return 3
        if re.search(r"low stress|not.*stressed|pretty calm|not much stress", r):
            return 2
        if re.search(r"very calm|relaxed|no stress|stress.free|completely calm", r):
            return 1
        return None

    def normalize_salt(self, raw: str) -> Optional[str]:
        r = raw.lower()
        if re.search(r"high salt|lots of salt|add salt|always salt|salty|love salt|"
                     r"processed food|fast food|crisps|chips|very salty", r):
            return "high"
        if re.search(r"low salt|rarely salt|avoid salt|no salt|little salt|barely", r):
            return "low"
        if re.search(r"moderate|average|sometimes|occasionally", r):
            return "moderate"
        return None

    def normalize_sugar_intake(self, raw: str) -> Optional[str]:
        r = raw.lower()
        if re.search(r"2.*day|3.*day|multiple.*day|every day|always|heavy", r):
            return "heavy"
        if re.search(r"1.*day|once a day|daily", r):
            return "daily"
        if re.search(r"once.*week|few.*week|occasional|rarely|1.3.*week", r):
            return "occasional"
        if re.search(r"never|don'?t|no.*soda|no.*juice|none|not really", r):
            return "none"
        return None

    def normalize_yes_no(self, raw: str) -> Optional[str]:
        r = raw.lower().strip()
        if re.search(r"^(yes|yeah|yep|yup|correct|affirmative|definitely|i do|i have|true)", r):
            return "yes"
        if re.search(r"^(no|nope|nah|negative|i don'?t|i haven'?t|false|not really)", r):
            return "no"
        if re.search(r"not sure|don'?t know|unsure|maybe|possibly", r):
            return "unknown"
        return None

    def normalize_all_lifestyle(self, message: str) -> Dict[str, Any]:
        """
        Extract all possible lifestyle keys from a single free-text message.
        Returns a dict of intermediate keys found.
        """
        results: Dict[str, Any] = {}
        msg = message.strip()

        activity = self.normalize_activity(msg)
        if activity:
            results["activity_level"] = activity

        diet = self.normalize_diet(msg)
        if diet:
            results["diet_quality"] = diet

        sleep = self.normalize_sleep(msg)
        if sleep:
            results["sleep_hours"] = sleep

        alcohol = self.normalize_alcohol(msg)
        if alcohol:
            results["alcohol_weekly"] = alcohol

        stress = self.normalize_stress(msg)
        if stress:
            results["stress_level"] = stress

        salt = self.normalize_salt(msg)
        if salt:
            results["salt_intake"] = salt

        sugar = self.normalize_sugar_intake(msg)
        if sugar:
            results["sugar_intake"] = sugar

        return results


# Singleton
answer_normalizer = AnswerNormalizer()
