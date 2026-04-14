"""
Behavior Aggregation Service
Calculates composite behavioral scores and generates insights from collected metrics.
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session
from models.session import InterviewSession
from models.behavior_metric import InterviewBehaviorMetric
from models.behavior_issue import BehaviorIssue


class BehaviorAggregationService:
    """
    Service for aggregating individual behavioral metrics into composite scores
    and generating data-driven insights about candidate presentation.
    """

    @staticmethod
    def calculate_composite_scores(metrics_list: List[InterviewBehaviorMetric]) -> Dict[str, float]:
        """
        Calculate composite behavior scores from individual metrics.
        
        Returns:
        - attention_score: 0-100 (eye contact + head stability)
        - presence_score: 0-100 (composure + facial stability)
        - vocal_confidence_score: 0-100 (speech quality + energy)
        - overall_behavior_score: 0-100 (weighted composite)
        """
        
        if not metrics_list:
            return {
                'attention_score': 0.0,
                'presence_score': 0.0,
                'vocal_confidence_score': 0.0,
                'overall_behavior_score': 0.0,
            }
        
        # Average individual scores
        avg_eye_contact = sum(m.eye_contact_score for m in metrics_list) / len(metrics_list)
        avg_head_stability = sum(m.head_stability_score for m in metrics_list) / len(metrics_list)
        avg_facial_stress = sum(m.facial_stress_index for m in metrics_list) / len(metrics_list)
        avg_blink = sum(m.blink_rate for m in metrics_list) / len(metrics_list)
        
        # Audio features (if available)
        avg_speech_stability = sum(m.speech_rate_stability or 0.5 for m in metrics_list) / len(metrics_list)
        avg_hesitation = sum(m.pause_hesitation or 0.5 for m in metrics_list) / len(metrics_list)
        avg_pitch = sum(m.pitch_variation or 0.5 for m in metrics_list) / len(metrics_list)
        avg_energy = sum(m.vocal_energy or 0.5 for m in metrics_list) / len(metrics_list)
        
        # Composite scores (normalize 0-1 to 0-100)
        # Attention = Eye contact + Head stability (averages 0-1)
        attention_score = ((avg_eye_contact + avg_head_stability) / 2) * 100
        
        # Presence = Head stability + composure (inverse of stress)
        presence_score = ((avg_head_stability + (1.0 - avg_facial_stress)) / 2) * 100
        
        # Vocal confidence = Speech stability + Energy + Pitch variation
        vocal_confidence_score = ((avg_speech_stability + avg_energy + avg_pitch) / 3) * 100
        
        # Overall = Weighted composite
        # 40% visual (attention + presence), 40% vocal, 20% comfort (hesitation inverse)
        overall_behavior_score = (
            (attention_score + presence_score) / 2 * 0.40 +
            vocal_confidence_score * 0.40 +
            (1.0 - avg_hesitation) * 100 * 0.20
        )
        
        return {
            'attention_score': round(attention_score, 2),
            'presence_score': round(presence_score, 2),
            'vocal_confidence_score': round(vocal_confidence_score, 2),
            'overall_behavior_score': round(overall_behavior_score, 2),
        }

    @staticmethod
    def aggregate_issues(session_id: int, db: Session) -> Dict[str, Any]:
        """
        Aggregate behavior issues from the session and generate insights.
        
        Returns:
        - issue_summary: Structured issue data
        - insights: Text-based behavioral insights
        - percentages: Issue occurrence percentages
        """
        
        issues = db.query(BehaviorIssue).filter(
            BehaviorIssue.session_id == session_id
        ).all()
        
        metrics = db.query(InterviewBehaviorMetric).filter(
            InterviewBehaviorMetric.session_id == session_id
        ).all()
        
        if not metrics:
            return {
                'issue_summary': {},
                'insights': 'No behavioral data collected during this session.',
                'percentages': {},
                'attention_level': 'Unknown',
                'presence_level': 'Good'
            }
        
        # Aggregate issue counts
        total_metrics = len(metrics)
        looking_away_total = sum(m.looking_away_count or 0 for m in metrics)
        multiple_faces_total = sum(m.multiple_faces_detected or 0 for m in metrics)
        face_absent_total = sum(m.face_absent_count or 0 for m in metrics)
        
        # Calculate percentages
        looking_away_pct = round((looking_away_total / total_metrics * 100), 1) if total_metrics > 0 else 0
        multiple_faces_pct = round((multiple_faces_total / total_metrics * 100), 1) if total_metrics > 0 else 0
        face_absent_pct = round((face_absent_total / total_metrics * 100), 1) if total_metrics > 0 else 0
        
        # Determine attention level
        if looking_away_pct >= 30 or face_absent_pct >= 20:
            attention_level = 'Low'
            attention_icon = '⚠️'
        elif looking_away_pct >= 15:
            attention_level = 'Moderate'
            attention_icon = '→'
        else:
            attention_level = 'High'
            attention_icon = '✅'
        
        # Generate insights
        insights = BehaviorAggregationService._generate_insights(
            looking_away_pct, face_absent_pct, attention_level, total_metrics
        )
        
        return {
            'issue_summary': {
                'looking_away_instances': looking_away_total,
                'multiple_faces_detected': multiple_faces_total,
                'face_absent_instances': face_absent_total,
            },
            'percentages': {
                'looking_away_pct': looking_away_pct,
                'multiple_faces_pct': multiple_faces_pct,
                'face_absent_pct': face_absent_pct,
            },
            'insights': insights,
            'attention_level': attention_level,
            'attention_icon': attention_icon,
            'total_samples': total_metrics,
        }

    @staticmethod
    def _generate_insights(looking_away_pct: float, face_absent_pct: float, 
                          attention_level: str, total_metrics: int) -> str:
        """Generate human-readable insights about behavioral patterns."""
        
        insights = []
        
        # Base insight
        attention_msg = {
            'High': f'Candidate showed strong focus and engagement throughout ({100 - looking_away_pct:.0f}% eye contact maintained).',
            'Moderate': f'Candidate showed moderate attention with occasional distractions ({100 - looking_away_pct:.0f}% eye contact).',
            'Low': f'Candidate showed low attention levels ({looking_away_pct:.0f}% distraction instances detected).',
        }
        insights.append(attention_msg.get(attention_level, 'Attention level assessment unavailable.'))
        
        # Specific issues
        if looking_away_pct > 0:
            if looking_away_pct > 30:
                insights.append(f'⚠️  Looking away detected frequently ({looking_away_pct:.0f}% of samples). Maintain eye contact with camera as if looking at interviewer.')
            elif looking_away_pct > 15:
                insights.append(f'Looking away observed {looking_away_pct:.0f}% of the time. Try to maintain steady eye contact with the camera.')
        
        if face_absent_pct > 10:
            insights.append(f'⚠️  Face not clearly visible {face_absent_pct:.0f}% of clips. Ensure proper camera positioning and lighting.')
        
        # Positive reinforcement
        if looking_away_pct <= 10 and face_absent_pct <= 5:
            insights.append('✅ Professional presentation with consistent eye contact and clear visibility.')
        
        return ' '.join(insights) if insights else 'Behavioral analysis complete.'

    @staticmethod
    def calculate_behavior_influenced_confidence(
        base_confidence: float,
        behavior_score: float,
        weights: Dict[str, float] = None
    ) -> float:
        """
        Apply behavior metrics to confidence score while maintaining transparency.
        
        Formula:
        final_confidence = base_confidence * (1 + behavior_influence)
        where behavior_influence is weighted behavioral contribution
        
        This AMPLIFIES confidence, never reduces it (behavior doesn't penalize).
        """
        
        if weights is None:
            weights = {
                'attention': 0.1,
                'presence': 0.05,
                'vocal': 0.05,
            }
        
        # Normalize behavior_score (0-100) to 0-1 range
        behavior_influence = (behavior_score / 100.0) * (
            weights['attention'] + weights['presence'] + weights['vocal']
        )
        
        # Final confidence (capped at 100)
        final_confidence = min(100.0, base_confidence * (1.0 + behavior_influence))
        
        return round(final_confidence, 2)

    @staticmethod
    def aggregate_session_behavior(session_id: int, db: Session) -> Dict[str, Any]:
        """
        Complete behavior aggregation for a session.
        Returns all metrics, scores, and insights in one call.
        """
        
        metrics = db.query(InterviewBehaviorMetric).filter(
            InterviewBehaviorMetric.session_id == session_id
        ).all()
        
        if not metrics:
            return {
                'behavior_score': 0.0,
                'attention_score': 0.0,
                'presence_score': 0.0,
                'vocal_confidence_score': 0.0,
                'insights': 'No behavioral data collected.',
                'issue_summary': {},
            }
        
        # Calculate composite scores
        composite = BehaviorAggregationService.calculate_composite_scores(metrics)
        
        # Aggregate issues
        issues_data = BehaviorAggregationService.aggregate_issues(session_id, db)
        
        return {
            'attention_score': composite['attention_score'],
            'presence_score': composite['presence_score'],
            'vocal_confidence_score': composite['vocal_confidence_score'],
            'overall_behavior_score': composite['overall_behavior_score'],
            'insights': issues_data['insights'],
            'attention_level': issues_data['attention_level'],
            'issue_percentages': issues_data['percentages'],
            'issue_summary': issues_data['issue_summary'],
            'total_samples': len(metrics),
        }
