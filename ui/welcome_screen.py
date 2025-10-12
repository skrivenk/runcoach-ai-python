"""Welcome Screen Widget"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal

class WelcomeScreen(QWidget):
    create_plan_clicked = Signal()  # Changed from pyqtSignal to Signal

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the welcome screen UI"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main content container
        content = QWidget()
        content.setMaximumWidth(800)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(48)

        # Title
        title = QLabel("Welcome to RunCoach AI")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Subtitle
        subtitle = QLabel("Your intelligent training companion powered by AI")
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)

        # Features grid
        features = QHBoxLayout()
        features.setSpacing(32)

        # Feature cards
        feature1 = self.create_feature_card(
            "📅",
            "Smart Calendar",
            "Adaptive training plans that adjust to your progress"
        )
        feature2 = self.create_feature_card(
            "🤖",
            "AI Coaching",
            "Personalized guidance from OpenAI-powered coach"
        )
        feature3 = self.create_feature_card(
            "📊",
            "Progress Tracking",
            "Real-time goal attainability and recommendations"
        )

        features.addWidget(feature1)
        features.addWidget(feature2)
        features.addWidget(feature3)

        content_layout.addLayout(features)

        # Call to action
        cta_layout = QVBoxLayout()
        cta_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cta_layout.setSpacing(16)

        create_btn = QPushButton("Create Your First Training Plan")
        create_btn.setObjectName("ctaButton")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self.create_plan_clicked.emit)

        import_btn = QPushButton("Import Existing Plan")
        import_btn.setObjectName("secondaryButton")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        cta_layout.addWidget(create_btn)
        cta_layout.addWidget(import_btn)

        content_layout.addLayout(cta_layout)

        content.setLayout(content_layout)
        layout.addWidget(content)

        self.setLayout(layout)
        self.apply_styles()

    def create_feature_card(self, icon: str, title: str, description: str) -> QFrame:
        """Create a feature card"""
        card = QFrame()
        card.setObjectName("featureCard")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setObjectName("featureIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("featureDescription")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        card.setLayout(layout)
        return card

    def apply_styles(self):
        """Apply custom styles"""
        self.setStyleSheet("""
            QLabel#welcomeTitle {
                font-size: 48px;
                color: #2c3e50;
                font-weight: bold;
            }

            QLabel#welcomeSubtitle {
                font-size: 20px;
                color: #7f8c8d;
                margin-bottom: 24px;
            }

            QFrame#featureCard {
                background-color: white;
                border-radius: 12px;
                padding: 24px;
                min-width: 200px;
            }

            QLabel#featureIcon {
                font-size: 48px;
            }

            QLabel#featureTitle {
                font-size: 20px;
                color: #2c3e50;
                font-weight: bold;
            }

            QLabel#featureDescription {
                font-size: 14px;
                color: #7f8c8d;
                line-height: 1.6;
            }

            QPushButton#ctaButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 16px 32px;
                font-size: 16px;
                font-weight: 500;
                min-width: 300px;
            }

            QPushButton#ctaButton:hover {
                background-color: #2980b9;
            }

            QPushButton#secondaryButton {
                background-color: transparent;
                color: #3498db;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton#secondaryButton:hover {
                background-color: rgba(52, 152, 219, 0.1);
            }
        """)