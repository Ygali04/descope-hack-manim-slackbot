import re
import os
import asyncio
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class ManimGenerator:
    """Secure Manim script generator using predefined templates"""
    
    def __init__(self):
        self.forbidden_imports = {
            'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
            'pickle', 'eval', 'exec', 'compile', 'open', '__import__',
            'input', 'raw_input', 'file', 'execfile'
        }
        
        self.forbidden_patterns = [
            r'\b(exec|eval|compile|__import__|getattr|setattr|delattr)\s*\(',
            r'\b(open|file)\s*\(',
            r'__(.*?)__',  # Dunder methods (except specific allowed ones)
            r'import\s+(os|sys|subprocess|socket|requests|urllib|pickle)',
            r'from\s+(os|sys|subprocess|socket|requests|urllib|pickle)',
        ]
        
        self.allowed_manim_imports = {
            'manim', 'numpy', 'math', 'random', 'colorsys'
        }

    async def generate_script(self, topic: str, render_params: Dict[str, Any]) -> str:
        """Generate safe Manim script based on topic"""
        
        # Sanitize topic
        safe_topic = self._sanitize_topic(topic)
        
        # Determine the best template based on topic
        template_type = self._classify_topic(safe_topic)
        
        # Generate script using appropriate template
        script = self._generate_from_template(template_type, safe_topic, render_params)
        
        # Validate generated script for security
        self._validate_script_security(script)
        
        logger.info("Generated Manim script", topic=safe_topic, template=template_type)
        return script

    def _sanitize_topic(self, topic: str) -> str:
        """Sanitize topic to prevent injection"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>\'"`;\\\n\r]', '', topic)
        # Limit length
        sanitized = sanitized[:100]
        # Ensure it's educational content
        if not sanitized.strip():
            sanitized = "Mathematical Concept"
        return sanitized.strip()

    def _classify_topic(self, topic: str) -> str:
        """Classify topic to determine appropriate template"""
        topic_lower = topic.lower()
        
        # Physics/Motion topics
        if any(word in topic_lower for word in ['motion', 'wave', 'oscillation', 'pendulum', 'force', 'gravity']):
            return 'physics_motion'
        
        # Math equation topics  
        if any(word in topic_lower for word in ['equation', 'algebra', 'quadratic', 'function', 'graph']):
            return 'math_equation'
        
        # Geometry topics
        if any(word in topic_lower for word in ['geometry', 'triangle', 'circle', 'polygon', 'theorem']):
            return 'geometry'
        
        # Biology/Chemistry processes
        if any(word in topic_lower for word in ['cell', 'dna', 'photosynthesis', 'respiration', 'molecule']):
            return 'biology_process'
        
        # Default to general educational
        return 'general_educational'

    def _generate_from_template(self, template_type: str, topic: str, render_params: Dict[str, Any]) -> str:
        """Generate script from predefined secure templates"""
        
        # Get video parameters
        width = render_params.get('width', 1280)
        height = render_params.get('height', 720)
        duration = min(render_params.get('duration_s', 30), 60)  # Cap at 60 seconds
        
        templates = {
            'physics_motion': self._physics_motion_template,
            'math_equation': self._math_equation_template,
            'geometry': self._geometry_template,
            'biology_process': self._biology_process_template,
            'general_educational': self._general_educational_template
        }
        
        template_func = templates.get(template_type, self._general_educational_template)
        return template_func(topic, duration)

    def _physics_motion_template(self, topic: str, duration: int) -> str:
        """Template for physics/motion topics"""
        return f'''
from manim import *
import numpy as np

class EducationalVideo(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=48, color=BLUE)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Create coordinate system
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            axis_config={{"color": GRAY}}
        )
        self.play(Create(axes))
        
        # Create moving object (simple harmonic motion example)
        dot = Dot(color=RED, radius=0.1)
        path = axes.plot(lambda x: 2 * np.sin(x), color=YELLOW)
        
        self.play(Create(path))
        self.play(MoveAlongPath(dot, path, rate_func=linear), run_time={duration * 0.6})
        
        # Add explanation text
        explanation = Text("Motion follows mathematical patterns", font_size=24)
        explanation.to_edge(DOWN)
        self.play(Write(explanation))
        self.wait({duration * 0.3})
        
        # Fade out
        self.play(FadeOut(Group(*self.mobjects)))
'''

    def _math_equation_template(self, topic: str, duration: int) -> str:
        """Template for mathematical equations"""
        return f'''
from manim import *
import numpy as np

class EducationalVideo(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=48, color=BLUE)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Mathematical equation (safe examples)
        equation = MathTex(r"f(x) = ax^2 + bx + c", font_size=60)
        self.play(Write(equation))
        self.wait(2)
        
        # Transform to specific example
        specific = MathTex(r"f(x) = x^2 - 4x + 3", font_size=60)
        self.play(Transform(equation, specific))
        self.wait(2)
        
        # Show graph
        axes = Axes(x_range=[-1, 5, 1], y_range=[-2, 6, 1])
        graph = axes.plot(lambda x: x**2 - 4*x + 3, color=YELLOW)
        
        self.play(equation.animate.to_edge(UP))
        self.play(Create(axes))
        self.play(Create(graph))
        
        # Highlight key points
        vertex = Dot(axes.c2p(2, -1), color=RED)
        vertex_label = Text("Vertex", font_size=24).next_to(vertex, DOWN)
        
        self.play(Create(vertex), Write(vertex_label))
        self.wait({duration * 0.4})
        
        self.play(FadeOut(Group(*self.mobjects)))
'''

    def _geometry_template(self, topic: str, duration: int) -> str:
        """Template for geometry topics"""
        return f'''
from manim import *
import numpy as np

class EducationalVideo(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=48, color=BLUE)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Create geometric shapes
        triangle = Triangle(color=YELLOW, fill_opacity=0.3)
        circle = Circle(radius=1.5, color=GREEN, fill_opacity=0.2)
        square = Square(side_length=2, color=RED, fill_opacity=0.2)
        
        # Arrange shapes
        shapes = Group(triangle, circle, square).arrange(RIGHT, buff=1)
        
        self.play(Create(triangle))
        self.wait(0.5)
        self.play(Create(circle))
        self.wait(0.5)
        self.play(Create(square))
        self.wait(1)
        
        # Show relationships
        self.play(shapes.animate.scale(0.7).to_edge(LEFT))
        
        # Add formulas
        formulas = VGroup(
            MathTex(r"A = \\frac{{1}}{{2}}bh", font_size=36),
            MathTex(r"A = \\pi r^2", font_size=36),
            MathTex(r"A = s^2", font_size=36)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(RIGHT)
        
        for formula in formulas:
            self.play(Write(formula))
            self.wait(0.5)
        
        self.wait({duration * 0.3})
        self.play(FadeOut(Group(*self.mobjects)))
'''

    def _biology_process_template(self, topic: str, duration: int) -> str:
        """Template for biology/chemistry processes"""
        return f'''
from manim import *
import numpy as np

class EducationalVideo(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=48, color=GREEN)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Create process diagram
        start = Circle(radius=0.5, color=BLUE, fill_opacity=0.7)
        start_label = Text("Start", font_size=20).move_to(start)
        
        arrow1 = Arrow(start.get_right(), start.get_right() + RIGHT * 2)
        
        middle = Rectangle(width=1.5, height=1, color=YELLOW, fill_opacity=0.5)
        middle.next_to(arrow1, RIGHT)
        middle_label = Text("Process", font_size=18).move_to(middle)
        
        arrow2 = Arrow(middle.get_right(), middle.get_right() + RIGHT * 2)
        
        end = Circle(radius=0.5, color=RED, fill_opacity=0.7)
        end.next_to(arrow2, RIGHT)
        end_label = Text("Result", font_size=20).move_to(end)
        
        # Animate process
        self.play(Create(start), Write(start_label))
        self.wait(0.5)
        self.play(GrowArrow(arrow1))
        self.play(Create(middle), Write(middle_label))
        self.wait(0.5)
        self.play(GrowArrow(arrow2))
        self.play(Create(end), Write(end_label))
        
        # Add descriptive text
        description = Text("Biological processes follow systematic steps", 
                         font_size=24).to_edge(DOWN)
        self.play(Write(description))
        
        self.wait({duration * 0.4})
        self.play(FadeOut(Group(*self.mobjects)))
'''

    def _general_educational_template(self, topic: str, duration: int) -> str:
        """General template for educational content"""
        return f'''
from manim import *
import numpy as np

class EducationalVideo(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=48, color=PURPLE)
        self.play(Write(title))
        self.wait(2)
        
        # Subtitle
        subtitle = Text("An Educational Exploration", font_size=32, color=GRAY)
        subtitle.next_to(title, DOWN)
        self.play(Write(subtitle))
        self.wait(1)
        
        # Move title up
        self.play(Group(title, subtitle).animate.to_edge(UP))
        
        # Create visual elements
        concepts = VGroup()
        for i in range(3):
            concept = Circle(radius=0.8, color=BLUE, fill_opacity=0.3)
            concept_text = Text(f"Concept {{i+1}}", font_size=20).move_to(concept)
            concept_group = Group(concept, concept_text)
            concepts.add(concept_group)
        
        concepts.arrange(RIGHT, buff=1)
        
        # Animate concepts
        for concept in concepts:
            self.play(Create(concept))
            self.wait(0.5)
        
        # Connect concepts
        connections = VGroup()
        for i in range(len(concepts) - 1):
            line = Line(concepts[i].get_right(), concepts[i+1].get_left())
            connections.add(line)
        
        self.play(Create(connections))
        
        # Final message
        conclusion = Text("Understanding leads to knowledge", 
                         font_size=28, color=GOLD).to_edge(DOWN)
        self.play(Write(conclusion))
        
        self.wait({duration * 0.3})
        self.play(FadeOut(Group(*self.mobjects)))
'''

    def _validate_script_security(self, script: str) -> None:
        """Validate that generated script is secure"""
        
        # Check for forbidden imports
        for forbidden in self.forbidden_imports:
            if re.search(rf'\bimport\s+{forbidden}\b', script):
                raise ValueError(f"Forbidden import detected: {forbidden}")
            if re.search(rf'\bfrom\s+{forbidden}\b', script):
                raise ValueError(f"Forbidden import detected: from {forbidden}")
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                raise ValueError(f"Forbidden pattern detected: {pattern}")
        
        # Ensure only safe Manim constructs
        lines = script.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                # Validate imports
                import_parts = stripped.split()
                if len(import_parts) >= 2:
                    module = import_parts[1].split('.')[0]
                    if module not in self.allowed_manim_imports:
                        raise ValueError(f"Unauthorized import: {module}")
        
        logger.debug("Script security validation passed") 