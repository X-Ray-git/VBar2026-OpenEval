from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ReviewerAssessment:
    reviewer_name: str
    song_id: str
    song_name: str
    dimension_scores: Dict[str, str] = field(default_factory=dict)
    overall_score: str = ""
    comments: str = ""
    audience_comments: Dict[str, str] = field(default_factory=dict)
    extra_fields: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        self.song_id = str(self.song_id).strip()
        self.song_name = str(self.song_name).strip()
        self.overall_score = str(self.overall_score).strip()
        self.comments = str(self.comments).strip()

@dataclass
class Song:
    song_id: str
    song_name: str
    assessments: List[ReviewerAssessment] = field(default_factory=list)

@dataclass
class ReviewerInfo:
    reviewer_name: str
    declaration: str = ""

@dataclass
class EvaluationReport:
    songs: Dict[str, Song] = field(default_factory=dict)
    reviewers: Dict[str, ReviewerInfo] = field(default_factory=dict)

    def add_assessment(self, assessment: ReviewerAssessment):
        if not assessment.song_id:
            return
        
        if assessment.song_id not in self.songs:
            self.songs[assessment.song_id] = Song(
                song_id=assessment.song_id,
                song_name=assessment.song_name
            )
        self.songs[assessment.song_id].assessments.append(assessment)
        
    def add_reviewer_info(self, name: str, declaration: str):
        if name not in self.reviewers:
            self.reviewers[name] = ReviewerInfo(reviewer_name=name)
        if declaration:
            if self.reviewers[name].declaration:
                self.reviewers[name].declaration += "\n" + declaration
            else:
                self.reviewers[name].declaration = declaration
