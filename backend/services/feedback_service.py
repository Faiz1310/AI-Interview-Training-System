"""
Feedback Service - Generates structured, logic-driven feedback from interview performance.

Provides detailed insights on:
- Strengths (areas where candidate excelled)
- Weaknesses (areas needing improvement)
- Behavior observations (from detected issues)
- Overall assessment with actionable recommendations

All feedback is logic-driven based on scores, issues, and explanations.
No generic AI-generated text.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models.session import InterviewSession
from models.answer import InterviewAnswer
from models.behavior_issue import BehaviorIssue
from models.behavior_metric import InterviewBehaviorMetric
from services.behavior_aggregation_service import BehaviorAggregationService
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# SCORING CONFIGURATION - Configurable Weights & Thresholds
# ═══════════════════════════════════════════════════════════════════════════

SCORING_CONFIG = {
    "weights": {
        "correctness": {
            "weight": 0.50,
            "rationale": "Technical accuracy is primary indicator of interview readiness"
        },
        "clarity": {
            "weight": 0.30,
            "rationale": "Communication quality is critical for workplace effectiveness"
        },
        "confidence": {
            "weight": 0.20,
            "rationale": "Delivery and presence support effective communication"
        }
    },
    "performance_thresholds": {
        "excellent": 85,
        "good": 70,
        "satisfactory": 50,
        "needs_improvement": 0
    },
    "score_thresholds": {
        "high": 80,
        "medium": 60,
        "low": 0
    }
}


class FeedbackService:
    """Generate structured, explainable feedback from interview data."""
    
    @staticmethod
    def get_session_feedback(session_id: int, db: Session) -> Dict[str, Any]:
        """
        Generate comprehensive feedback for a completed session.
        
        Args:
            session_id: ID of the interview session
            db: Database session
            
        Returns:
            Dictionary with structured feedback
        """
        # Fetch session and validation
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            return {"error": "Session not found"}
        
        if session.status != "completed":
            return {"error": "Session must be completed to generate feedback"}
        
        # Fetch all answers for this session
        answers: List[InterviewAnswer] = db.query(InterviewAnswer).filter(
            InterviewAnswer.session_id == session_id
        ).order_by(InterviewAnswer.id).all()
        
        # Fetch behavior issues
        behavior_issues: List[BehaviorIssue] = db.query(BehaviorIssue).filter(
            BehaviorIssue.session_id == session_id
        ).all()
        
        # Fetch and aggregate behavior metrics
        behavior_metrics = db.query(InterviewBehaviorMetric).filter(
            InterviewBehaviorMetric.session_id == session_id
        ).all()
        
        behavior_aggregation = BehaviorAggregationService.aggregate_session_behavior(
            session_id, db
        )
        
        # Generate feedback components
        strengths = FeedbackService._extract_strengths(answers)
        weaknesses = FeedbackService._extract_weaknesses(answers)
        behavior_feedback = FeedbackService._extract_behavior_feedback(
            answers, behavior_issues
        )
        
        # Calculate metrics
        avg_correctness = sum(a.correctness for a in answers) / len(answers) if answers else 0
        avg_clarity = sum(a.clarity for a in answers) / len(answers) if answers else 0
        avg_confidence = sum(a.confidence for a in answers) / len(answers) if answers else 0
        
        overall_score = FeedbackService._calculate_overall_score(
            avg_correctness, avg_clarity, avg_confidence
        )
        
        # Calculate score breakdown with contributions
        score_breakdown = FeedbackService._calculate_score_breakdown(
            avg_correctness, avg_clarity, avg_confidence, len(behavior_issues)
        )
        
        final_recommendation = FeedbackService._generate_recommendation(
            answers, overall_score, behavior_issues
        )
        
        return {
            "session_id": session_id,
            "overall_score": overall_score,
            "performance_label": session.performance_label or _get_performance_label(overall_score),
            "score_breakdown": score_breakdown,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "behavior_feedback": behavior_feedback,
            "final_recommendation": final_recommendation,
            "total_questions": len(answers),
            "avg_correctness": avg_correctness,
            "avg_clarity": avg_clarity,
            "avg_confidence": avg_confidence,
            "behavioral_issues_detected": len(behavior_issues),
            "behavior_metrics": {
                "attention_score": behavior_aggregation.get('attention_score', 0),
                "presence_score": behavior_aggregation.get('presence_score', 0),
                "vocal_confidence_score": behavior_aggregation.get('vocal_confidence_score', 0),
                "overall_behavior_score": behavior_aggregation.get('overall_behavior_score', 0),
                "attention_level": behavior_aggregation.get('attention_level', 'Unknown'),
                "insights": behavior_aggregation.get('insights', 'No behavioral data available'),
                "issue_percentages": behavior_aggregation.get('issue_percentages', {}),
                "issue_summary": behavior_aggregation.get('issue_summary', {}),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def _extract_strengths(answers: List[InterviewAnswer]) -> List[Dict[str, Any]]:
        """
        Extract strengths based on high scores and explanations.
        
        Strengths are:
        - Questions with overall score >= 80
        - Questions with correctness >= 85
        - Multiple strong answers indicating patterns
        """
        strengths = []
        
        # Find high-scoring answers
        strong_answers = [a for a in answers if a.overall >= 80]
        
        if not strong_answers:
            return []
        
        # Analyze patterns in strong answers
        high_correctness = [a for a in strong_answers if a.correctness >= 85]
        high_clarity = [a for a in strong_answers if a.clarity >= 85]
        
        # Strength 1: Strong technical knowledge
        if high_correctness:
            strengths.append({
                "area": "Technical Knowledge",
                "confidence_level": "high" if len(high_correctness) > len(strong_answers) / 2 else "medium",
                "evidence": f"Scored {high_correctness[0].correctness:.0f}% on technical question: {high_correctness[0].question[:60]}...",
                "count": len(high_correctness),
            })
        
        # Strength 2: Clear communication
        if high_clarity:
            strengths.append({
                "area": "Communication Clarity",
                "confidence_level": "high" if len(high_clarity) > len(strong_answers) / 2 else "medium",
                "evidence": f"Explained concepts clearly (clarity score: {high_clarity[0].clarity:.0f}%)",
                "count": len(high_clarity),
            })
        
        # Strength 3: Consistent performance
        if len(strong_answers) >= answers.__len__() * 0.7 if answers else False:
            avg_score = sum(a.overall for a in strong_answers) / len(strong_answers)
            strengths.append({
                "area": "Consistency",
                "confidence_level": "high",
                "evidence": f"Maintained strong performance across questions (avg: {avg_score:.0f}%)",
                "count": len(strong_answers),
            })
        
        return strengths
    
    @staticmethod
    def _extract_weaknesses(answers: List[InterviewAnswer]) -> List[Dict[str, Any]]:
        """
        Extract weaknesses based on low scores and explanations.
        
        Weaknesses are:
        - Questions with overall score < 60
        - Correctness issues (low accuracy, misunderstandings)
        - Clarity issues (rambling, unclear explanations)
        - Confidence issues (hesitation, uncertainty)
        """
        weaknesses = []
        
        # Find low-scoring answers
        weak_answers = [a for a in answers if a.overall < 60]
        
        if not weak_answers:
            return []
        
        # Analyze patterns in weak answers
        low_correctness = [a for a in weak_answers if a.correctness < 50]
        low_clarity = [a for a in weak_answers if a.clarity < 50]
        low_confidence = [a for a in weak_answers if a.confidence < 50]
        
        # Weakness 1: Knowledge gaps - DATA-DRIVEN
        if low_correctness:
            avg_correctness_low = sum(a.correctness for a in low_correctness) / len(low_correctness)
            weakness_detail = {
                "area": "Technical Knowledge Gaps",
                "severity": "high" if len(low_correctness) > len(weak_answers) / 2 else "medium",
                "evidence": f"Correctness averaged {avg_correctness_low:.1f}% on {len(low_correctness)} question(s) - ({100 - avg_correctness_low:.0f}% below target)",
                "explanation": f"Struggled with: {low_correctness[0].question[:60]}... - {low_correctness[0].correctness_explanation or 'Inaccurate technical knowledge'}",
                "count": len(low_correctness),
                "metric": f"{avg_correctness_low:.1f}%"
            }
            weaknesses.append(weakness_detail)
        
        # Weakness 2: Unclear explanations - DATA-DRIVEN
        if low_clarity:
            avg_clarity_low = sum(a.clarity for a in low_clarity) / len(low_clarity)
            weakness_detail = {
                "area": "Explanation Clarity",
                "severity": "high" if len(low_clarity) > len(weak_answers) / 2 else "medium",
                "evidence": f"Clarity averaged {avg_clarity_low:.1f}% on {len(low_clarity)} question(s) - difficulty structuring responses",
                "explanation": f"Why this matters: Clear explanations help interviewers understand your thinking process. {low_clarity[0].clarity_explanation or 'Need to structure explanations better'}",
                "count": len(low_clarity),
                "metric": f"{avg_clarity_low:.1f}%"
            }
            weaknesses.append(weakness_detail)
        
        # Weakness 3: Lack of confidence - DATA-DRIVEN
        if low_confidence:
            avg_confidence_low = sum(a.confidence for a in low_confidence) / len(low_confidence)
            weakness_detail = {
                "area": "Confidence & Delivery",
                "severity": "medium",
                "evidence": f"Confidence averaged {avg_confidence_low:.1f}% on {len(low_confidence)} question(s) indicating hesitation",
                "explanation": f"Showed hesitation in answering. Work on speaking with conviction and maintaining calm, steady delivery. This affects interviewer perception of your readiness.",
                "count": len(low_confidence),
                "metric": f"{avg_confidence_low:.1f}%"
            }
            weaknesses.append(weakness_detail)
        
        return weaknesses
    
    @staticmethod
    def _extract_behavior_feedback(
        answers: List[InterviewAnswer],
        behavior_issues: List[BehaviorIssue]
    ) -> List[Dict[str, Any]]:
        """
        Extract and AGGREGATE behavioral feedback from detected issues.
        
        Instead of listing issues per-question, groups repeated issues and shows:
        - Issue type and frequency
        - Aggregated severity
        - Overall impact and recommendations
        """
        if not behavior_issues:
            return [{
                "observation": "No behavioral issues detected",
                "severity": "none",
                "details": "Maintained good eye contact and presence throughout",
                "frequency": None,
                "impact": None,
                "recommendation": None,
            }]
        
        feedback = []
        
        # AGGREGATE: Count issue types and frequencies
        issue_counts = {}
        issue_severities = {}  # Track severity per issue type
        
        for issue in behavior_issues:
            issue_type = issue.issue
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            
            if issue_type not in issue_severities:
                issue_severities[issue_type] = []
            issue_severities[issue_type].append(issue.severity)
        
        # Issue descriptions and handling
        issue_descriptions = {
            "face_not_present": "Face not visible in camera",
            "looking_away": "Did not maintain eye contact",
            "multiple_faces": "Multiple people detected",
        }
        
        # Generate AGGREGATED feedback for each issue type
        for issue_type, count in issue_counts.items():
            # Calculate average severity for this issue type
            avg_severity = _calculate_issue_severity(
                [issue for issue in behavior_issues if issue.issue == issue_type]
            )
            
            # DATA-DRIVEN: Include occurrence frequency as a metric
            feedback_item = {
                "observation": issue_descriptions.get(issue_type, issue_type),
                "severity": avg_severity,
                "frequency": f"Occurred {count} time(s) during the {len(answers)} questions",
                "impact": _get_behavior_impact(issue_type),
                "recommendation": _get_behavior_recommendation(issue_type),
                "count": count,
                "percentage": f"{(count / len(behavior_issues) * 100):.0f}%" if behavior_issues else "0%"
            }
            feedback.append(feedback_item)
        
        return feedback
    
    @staticmethod
    def _calculate_overall_score(
        correctness: float,
        clarity: float,
        confidence: float
    ) -> float:
        """
        Calculate overall score using CONFIGURABLE weighted formula.
        
        Uses weights from SCORING_CONFIG:
        - Correctness: 50% (technical knowledge is primary)
        - Clarity: 30% (communication matters)
        - Confidence: 20% (delivery and presence)
        
        Score is 0-100.
        """
        # Get weights from config
        weights = SCORING_CONFIG["weights"]
        
        # Weighted calculation
        overall = (
            correctness * weights["correctness"]["weight"] +
            clarity * weights["clarity"]["weight"] +
            confidence * weights["confidence"]["weight"]
        )
        
        # Round to nearest 0.1
        return round(overall, 1)
    
    @staticmethod
    def _calculate_score_breakdown(
        correctness: float,
        clarity: float,
        confidence: float,
        behavioral_issues_count: int
    ) -> Dict[str, Any]:
        """
        Calculate detailed score breakdown showing how each component contributes.
        
        Returns score_breakdown with:
        - Each metric: score, weight, contribution to overall
        - Behavior: issue count and severity assessment
        """
        weights = SCORING_CONFIG["weights"]
        
        # Calculate contributions to overall score
        correctness_contribution = correctness * weights["correctness"]["weight"]
        clarity_contribution = clarity * weights["clarity"]["weight"]
        confidence_contribution = confidence * weights["confidence"]["weight"]
        
        # Behavior assessment (not weighted into score, but provides context)
        behavior_assessment = "good" if behavioral_issues_count == 0 else \
                            "acceptable" if behavioral_issues_count <= 2 else \
                            "needs_attention"
        
        return {
            "correctness": {
                "score": round(correctness, 1),
                "weight": f"{weights['correctness']['weight'] * 100:.0f}%",
                "contribution": round(correctness_contribution, 2),
                "rationale": "Technical knowledge is the primary indicator"
            },
            "clarity": {
                "score": round(clarity, 1),
                "weight": f"{weights['clarity']['weight'] * 100:.0f}%",
                "contribution": round(clarity_contribution, 2),
                "rationale": "Communication quality affects workplace effectiveness"
            },
            "confidence": {
                "score": round(confidence, 1),
                "weight": f"{weights['confidence']['weight'] * 100:.0f}%",
                "contribution": round(confidence_contribution, 2),
                "rationale": "Delivery presence supports effective communication"
            },
            "behavior": {
                "issues_detected": behavioral_issues_count,
                "assessment": behavior_assessment,
                "note": "Behavioral factors do not reduce correctness scores - they provide context"
            }
        }
    
    @staticmethod
    def _generate_recommendation(
        answers: List[InterviewAnswer],
        overall_score: float,
        behavior_issues: List[BehaviorIssue]
    ) -> str:
        """
        Generate DATA-DRIVEN actionable recommendation based on performance.
        """
        if not answers:
            return "No interview data to analyze."
        
        avg_correctness = sum(a.correctness for a in answers) / len(answers)
        avg_clarity = sum(a.clarity for a in answers) / len(answers)
        avg_confidence = sum(a.confidence for a in answers) / len(answers)
        
        recommendations = []
        
        # Score-based recommendations - DATA-DRIVEN with specific metrics
        if overall_score >= 85:
            recommendations.append(
                f"Excellent performance! With a score of {overall_score:.1f}, you demonstrated strong technical knowledge "
                f"(correctness: {avg_correctness:.0f}%) and clear communication (clarity: {avg_clarity:.0f}%). "
                f"Consider taking on more challenging interview scenarios to further refine your skills."
            )
        elif overall_score >= 70:
            recommendations.append(
                f"Good foundation with score {overall_score:.1f}. Correctness is strong at {avg_correctness:.0f}%. "
                f"Focus on improving clarity ({avg_clarity:.0f}%) and confidence ({avg_confidence:.0f}%) "
                f"to elevate your overall performance."
            )
        elif overall_score >= 50:
            recommendations.append(
                f"Score of {overall_score:.1f} indicates significant opportunities. Correctness at {avg_correctness:.0f}% "
                f"needs strengthening, and clarity at {avg_clarity:.0f}% requires work. Prioritize technical fundamentals review "
                f"and practice explaining concepts step-by-step before your next interview."
            )
        else:
            recommendations.append(
                f"With a score of {overall_score:.1f}, more focused preparation is needed. Target technical fundamentals "
                f"(current correctness: {avg_correctness:.0f}%) and work on structuring your explanations clearly. "
                f"Review common interview questions and practice articulating your knowledge."
            )
        
        # Weakness-based recommendations
        low_score_answers = [a for a in answers if a.overall < 60]
        if low_score_answers:
            weak_topics = [a.question[:40] for a in low_score_answers[:2]]
            recommendations.append(
                f"Specifically review these challenging topics: {', '.join(weak_topics)}. "
                f"Study the underlying concepts and practice explaining them without external resources."
            )
        
        # Behavior-based recommendations
        if behavior_issues:
            if len(behavior_issues) > 5:
                recommendations.append(
                    f"Behavioral notes: {len(behavior_issues)} issues detected. Ensure your face is clearly visible in the camera, "
                    f"maintain eye contact with the lens, and minimize distractions in your environment."
                )
        else:
            recommendations.append(
                "Excellent camera presence throughout the interview! Maintain this strong presence in future sessions."
            )
        
        # Confidence-specific recommendation
        if avg_confidence < 60:
            recommendations.append(
                f"Your confidence level ({avg_confidence:.0f}%) can be improved by practicing your answers beforehand, "
                f"taking deliberate pauses to think, and speaking with conviction even when uncertain."
            )
        
        # Combine recommendations with spacing
        return " ".join(recommendations)


def _get_performance_label(score: float) -> str:
    """Get performance label based on score."""
    if score >= 85:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Satisfactory"
    else:
        return "Needs Improvement"


def _calculate_issue_severity(issues: List[BehaviorIssue]) -> str:
    """Calculate average severity of behavior issues."""
    if not issues:
        return "none"
    
    severity_scores = {
        "low": 0,
        "medium": 1,
        "high": 2,
    }
    
    avg_severity = sum(
        severity_scores.get(issue.severity, 0) for issue in issues
    ) / len(issues)
    
    if avg_severity < 0.5:
        return "low"
    elif avg_severity < 1.5:
        return "medium"
    else:
        return "high"


def _get_behavior_impact(issue_type: str) -> str:
    """Describe impact of behavioral issue."""
    impacts = {
        "face_not_present": "Reduces evaluator's ability to assess presence and engagement",
        "looking_away": "May appear disengaged or uncertain",
        "multiple_faces": "Can be distracting and unprofessional",
    }
    return impacts.get(issue_type, "May affect interview impression")


def _get_behavior_recommendation(issue_type: str) -> str:
    """Provide recommendation for behavioral issue."""
    recommendations = {
        "face_not_present": "Adjust camera position to keep face centered and visible at all times",
        "looking_away": "Look directly at the camera lens when speaking to maintain eye contact",
        "multiple_faces": "Ensure you're alone in the room during the interview",
    }
    return recommendations.get(issue_type, "Review camera setup and positioning")


def generate_feedback_report(
    session_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    High-level function to generate complete feedback report.
    
    Args:
        session_id: Interview session ID
        db: Database session
        
    Returns:
        Complete feedback report with all sections
    """
    return FeedbackService.get_session_feedback(session_id, db)
