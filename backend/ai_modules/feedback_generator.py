"""
Feedback generator module.
Generates supportive, non-judgmental feedback based on interview performance.
Provides:
  - Per-question feedback
  - Session summary coaching
  - Real-time supportive nudges when stress/hesitation detected
  - Improvement recommendations
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_answer_feedback(
    correctness: float,
    clarity: float,
    confidence: float,
    overall: float,
    correctness_explanation: str = "",
    clarity_explanation: str = "",
    improvement_tip: str = "",
) -> Dict:
    """
    Generate structured feedback for a single answer.
    Combines AI-generated explanations with rule-based coaching.
    """
    feedback = {
        "summary": "",
        "strengths": [],
        "areas_to_improve": [],
        "coaching_tip": "",
    }

    # Identify strengths
    if correctness >= 75:
        feedback["strengths"].append("Strong knowledge and accuracy in your response.")
    if clarity >= 75:
        feedback["strengths"].append("Clear and well-structured explanation.")
    if confidence >= 75:
        feedback["strengths"].append("Confident and composed delivery.")

    # Identify areas to improve
    if correctness < 50:
        feedback["areas_to_improve"].append("Review the core concepts related to this question.")
    elif correctness < 75:
        feedback["areas_to_improve"].append("Good foundation, but some key points were missed.")

    if clarity < 50:
        feedback["areas_to_improve"].append("Try structuring your answer with a clear beginning, middle, and end.")
    elif clarity < 75:
        feedback["areas_to_improve"].append("Reduce filler words and aim for more concise explanations.")

    if confidence < 50:
        feedback["areas_to_improve"].append("Practice speaking at a steady pace with good eye contact.")
    elif confidence < 75:
        feedback["areas_to_improve"].append("You're on the right track — keep building confidence through practice.")

    # Overall summary
    if overall >= 80:
        feedback["summary"] = "Excellent response! You demonstrated strong command of the topic."
    elif overall >= 60:
        feedback["summary"] = "Good response with room for improvement in some areas."
    elif overall >= 40:
        feedback["summary"] = "You showed some understanding, but there are significant areas to work on."
    else:
        feedback["summary"] = "This is a challenging area for you. Focus on building foundational knowledge."

    # Coaching tip
    if improvement_tip:
        feedback["coaching_tip"] = improvement_tip
    elif correctness < clarity and correctness < confidence:
        feedback["coaching_tip"] = "Focus on deepening your technical knowledge. Review key concepts and practice explaining them."
    elif clarity < correctness and clarity < confidence:
        feedback["coaching_tip"] = "Practice the STAR method: Situation, Task, Action, Result. This helps structure your answers."
    else:
        feedback["coaching_tip"] = "Practice mock interviews to build confidence. Record yourself and review your delivery."

    return feedback


def generate_session_summary(
    overall_score: float,
    correctness_score: float,
    clarity_score: float,
    confidence_score: float,
    total_questions: int,
    answers_data: Optional[List[Dict]] = None,
) -> Dict:
    """
    Generate a comprehensive session summary with coaching feedback.
    """
    scores = {
        "Correctness": correctness_score,
        "Clarity": clarity_score,
        "Confidence": confidence_score,
    }
    strongest = max(scores, key=scores.get)
    weakest = min(scores, key=scores.get)

    # Performance label
    if overall_score >= 85:
        label = "Strong Candidate"
        message = "Excellent work! You demonstrate strong command of the subject. Focus on polishing advanced communication skills."
    elif overall_score >= 70:
        label = "Good Performance"
        message = f"Good overall performance. Your main area to improve is {weakest.lower()}. Practice will close this gap quickly."
    elif overall_score >= 50:
        label = "Needs Improvement"
        message = f"There is clear room for growth, especially in {weakest.lower()}. Consider practicing with structured answer frameworks like STAR."
    else:
        label = "Critical Improvement Needed"
        message = "Significant improvement needed across all areas. Start by reviewing fundamentals and practice daily mock interviews."

    # Detailed recommendations
    recommendations = []

    if correctness_score < 60:
        recommendations.append({
            "area": "Knowledge",
            "priority": "high",
            "suggestion": "Review core technical concepts. Create flashcards for key topics and practice explaining them aloud.",
        })
    elif correctness_score < 80:
        recommendations.append({
            "area": "Knowledge",
            "priority": "medium",
            "suggestion": "Strengthen edge cases and advanced topics. Read documentation and practice with harder questions.",
        })

    if clarity_score < 60:
        recommendations.append({
            "area": "Communication",
            "priority": "high",
            "suggestion": "Practice structured responses using STAR method. Record yourself and listen back for filler words.",
        })
    elif clarity_score < 80:
        recommendations.append({
            "area": "Communication",
            "priority": "medium",
            "suggestion": "Work on reducing redundancy. Practice delivering concise, focused answers under time pressure.",
        })

    if confidence_score < 60:
        recommendations.append({
            "area": "Confidence",
            "priority": "high",
            "suggestion": "Practice with a friend or record yourself. Focus on maintaining eye contact and speaking steadily.",
        })
    elif confidence_score < 80:
        recommendations.append({
            "area": "Confidence",
            "priority": "medium",
            "suggestion": "You're building good habits. Continue practicing to make confident delivery feel natural.",
        })

    # Trend analysis from answers
    trend_insight = ""
    if answers_data and len(answers_data) >= 3:
        first_half = answers_data[: len(answers_data) // 2]
        second_half = answers_data[len(answers_data) // 2 :]
        first_avg = sum(a.get("overall", 0) for a in first_half) / len(first_half)
        second_avg = sum(a.get("overall", 0) for a in second_half) / len(second_half)
        if second_avg > first_avg + 5:
            trend_insight = "You showed improvement as the interview progressed. Keep building on that momentum!"
        elif second_avg < first_avg - 5:
            trend_insight = "Your performance dipped toward the end. Practice sustaining focus throughout longer interviews."

    return {
        "performance_label": label,
        "coach_message": message,
        "strongest_area": strongest,
        "weakest_area": weakest,
        "recommendations": recommendations,
        "trend_insight": trend_insight,
        "scores": {
            "overall": round(overall_score, 2),
            "correctness": round(correctness_score, 2),
            "clarity": round(clarity_score, 2),
            "confidence": round(confidence_score, 2),
        },
    }


def get_realtime_encouragement(
    confidence_score: float,
    stress_level: float,
    consecutive_low_scores: int = 0,
) -> Optional[str]:
    """
    Provide real-time supportive feedback when stress or low confidence is detected.
    This is encouragement, not correction.
    """
    if stress_level > 0.7 and confidence_score < 50:
        return "Take a moment and explain step by step. You've got this!"

    if stress_level > 0.6:
        return "You're doing well, continue calmly."

    if confidence_score < 40:
        return "Remember to breathe. Focus on one point at a time."

    if consecutive_low_scores >= 2:
        return "Every question is a fresh start. Take a breath and give it your best."

    return None
