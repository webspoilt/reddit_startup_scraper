"""
Output Generation Module
Handles saving analysis results to various file formats.
"""

import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class OutputManager:
    """
    Manages saving and exporting analysis results.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the output manager.

        Args:
            output_dir: Directory for output files. Defaults to config setting.
        """
        from config import Config
        config = Config()

        if output_dir is None:
            self.output_dir = config.output_directory
        else:
            self.output_dir = Path(output_dir)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track output files
        self.generated_files: List[Path] = []

    def _generate_timestamp(self) -> str:
        """Generate a timestamp string for filenames."""
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def save_markdown(
        self,
        analyses: List,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save analysis results to a Markdown file.

        Args:
            analyses: List of PostAnalysis objects to save.
            filename: Optional custom filename. Auto-generates if not provided.

        Returns:
            Path to the saved file.
        """
        if filename is None:
            timestamp = self._generate_timestamp()
            filename = f"startup_ideas_{timestamp}.md"

        filepath = self.output_dir / filename

        # Build the markdown content
        content_lines: List[str] = [
            "# Reddit Startup Idea Analysis Report",
            "",
            f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Posts Analyzed:** {len(analyses)}",
        ]

        # Get unique subreddits
        subreddits = set()
        for a in analyses:
            if hasattr(a, 'subreddit'):
                subreddits.add(a.subreddit)

        if subreddits:
            content_lines.append(f"**Source Subreddits:** {', '.join(sorted(subreddits))}")

        content_lines.extend([
            "",
            "---",
            "",
            "## Summary Statistics",
            "",
        ])

        # Add summary statistics
        startup_types: Dict[str, int] = {}
        total_confidence = 0.0

        for analysis in analyses:
            if hasattr(analysis, 'startup_type'):
                startup_type = analysis.startup_type
                startup_types[startup_type] = startup_types.get(startup_type, 0) + 1
            if hasattr(analysis, 'confidence_score'):
                total_confidence += float(analysis.confidence_score)

        avg_confidence = total_confidence / len(analyses) if analyses else 0

        content_lines.append(f"- **Average Confidence Score:** {avg_confidence:.2f}")
        content_lines.append("- **Idea Distribution:**")
        for startup_type, count in sorted(startup_types.items()):
            content_lines.append(f"  - {startup_type}: {count}")

        content_lines.extend([
            "",
            "---",
            "",
            "## Detailed Analysis",
            "",
        ])

        # Add each analysis
        for i, analysis in enumerate(analyses, 1):
            # Get analysis attributes safely
            if hasattr(analysis, 'to_markdown'):
                content_lines.append(f"### Idea #{i}: {analysis.startup_type}")
                content_lines.append("")
                content_lines.append(analysis.to_markdown())
            else:
                content_lines.append(f"### Idea #{i}")
                if hasattr(analysis, 'startup_idea'):
                    content_lines.append(f"**Idea:** {analysis.startup_idea}")
                if hasattr(analysis, 'core_problem_summary'):
                    content_lines.append(f"**Problem:** {analysis.core_problem_summary}")
                if hasattr(analysis, 'target_audience'):
                    content_lines.append(f"**Audience:** {analysis.target_audience}")
                if hasattr(analysis, 'startup_type'):
                    content_lines.append(f"**Type:** {analysis.startup_type}")
                if hasattr(analysis, 'confidence_score'):
                    content_lines.append(f"**Confidence:** {analysis.confidence_score:.2f}")

            content_lines.extend([
                "",
                "---",
                "",
            ])

        # Write to file
        content = "\n".join(content_lines)
        filepath.write_text(content, encoding="utf-8")

        self.generated_files.append(filepath)
        logger.info(f"Saved Markdown report to {filepath}")

        return filepath

    def save_csv(
        self,
        analyses: List,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save analysis results to a CSV file.

        Args:
            analyses: List of PostAnalysis objects to save.
            filename: Optional custom filename. Auto-generates if not provided.

        Returns:
            Path to the saved file.
        """
        import pandas as pd

        if filename is None:
            timestamp = self._generate_timestamp()
            filename = f"startup_ideas_{timestamp}.csv"

        filepath = self.output_dir / filename

        # Convert analyses to list of dictionaries
        data = []
        for analysis in analyses:
            if hasattr(analysis, 'to_dict'):
                data.append(analysis.to_dict())
            else:
                data.append(asdict(analysis))

        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)

        # Reorder columns for better readability
        column_order = [
            "original_title",
            "subreddit",
            "core_problem_summary",
            "target_audience",
            "startup_idea",
            "startup_type",
            "estimated_complexity",
            "potential_market_size",
            "confidence_score",
            "post_url",
            "model_used",
            "analysis_timestamp",
        ]

        # Only include columns that exist
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]

        df.to_csv(filepath, index=False, encoding="utf-8")

        self.generated_files.append(filepath)
        logger.info(f"Saved CSV report to {filepath}")

        return filepath

    def save_json(
        self,
        analyses: List,
        filename: Optional[str] = None,
        pretty: bool = True,
    ) -> Path:
        """
        Save analysis results to a JSON file.

        Args:
            analyses: List of PostAnalysis objects to save.
            filename: Optional custom filename. Auto-generates if not provided.
            pretty: Whether to format JSON with indentation.

        Returns:
            Path to the saved file.
        """
        if filename is None:
            timestamp = self._generate_timestamp()
            filename = f"startup_ideas_{timestamp}.json"

        filepath = self.output_dir / filename

        # Convert analyses to list of dictionaries
        model_used = "gemini-1.5-flash"
        if analyses and hasattr(analyses[0], 'model_used'):
            model_used = analyses[0].model_used

        analyses_data = []
        for analysis in analyses:
            if hasattr(analysis, 'to_dict'):
                analyses_data.append(analysis.to_dict())
            else:
                analyses_data.append(asdict(analysis))

        data = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total_analyses": len(analyses),
                "model_used": model_used,
            },
            "analyses": analyses_data,
        }

        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)

        self.generated_files.append(filepath)
        logger.info(f"Saved JSON report to {filepath}")

        return filepath

    def save_all_formats(
        self,
        analyses: List,
    ) -> Dict[str, Path]:
        """
        Save analysis results to all supported formats.

        Args:
            analyses: List of PostAnalysis objects to save.

        Returns:
            Dictionary mapping format names to file paths.
        """
        from config import Config
        config = Config()

        results: Dict[str, Path] = {}

        output_format = config.output_format

        if output_format in ["markdown", "both"]:
            results["markdown"] = self.save_markdown(analyses)

        if output_format in ["csv", "both"]:
            results["csv"] = self.save_csv(analyses)

        if output_format in ["json", "both"]:
            results["json"] = self.save_json(analyses)

        return results

    def get_generated_files(self) -> List[Path]:
        """
        Get list of all files generated by this manager.

        Returns:
            List of Path objects.
        """
        return self.generated_files


def print_summary(analyses: List) -> None:
    """
    Print a summary of the analysis results to the console.

    Args:
        analyses: List of PostAnalysis objects.
    """
    if not analyses:
        print("\nNo analyses to display.")
        return

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE!")
    print("=" * 60)

    # Count by startup type
    type_counts: Dict[str, int] = {}
    total_confidence = 0.0

    for analysis in analyses:
        if hasattr(analysis, 'startup_type'):
            startup_type = analysis.startup_type
            type_counts[startup_type] = type_counts.get(startup_type, 0) + 1
        if hasattr(analysis, 'confidence_score'):
            total_confidence += float(analysis.confidence_score)

    avg_confidence = total_confidence / len(analyses) if analyses else 0

    print(f"\nResults Summary:")
    print(f"   - Total ideas generated: {len(analyses)}")
    print(f"   - Average confidence score: {avg_confidence:.2f}")
    print(f"   - Idea breakdown:")
    for startup_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"     - {startup_type}: {count}")

    from config import Config
    config = Config()
    print(f"\nOutput files saved to: {config.output_directory}")
    print("=" * 60 + "\n")


def save_quick_summary(analyses: List) -> str:
    """
    Generate a quick text summary for console display.

    Args:
        analyses: List of PostAnalysis objects.

    Returns:
        Formatted summary string.
    """
    if not analyses:
        return "No analyses generated."

    lines: List[str] = [
        "\nTOP STARTUP IDEAS:",
        "-" * 40,
    ]

    for i, analysis in enumerate(analyses[:5], 1):  # Show top 5
        idea_text = ""
        problem_text = ""
        confidence_text = ""
        complexity_text = ""

        if hasattr(analysis, 'startup_idea'):
            idea_text = str(analysis.startup_idea)[:60]
        if hasattr(analysis, 'core_problem_summary'):
            problem_text = str(analysis.core_problem_summary)[:80]
        if hasattr(analysis, 'confidence_score'):
            confidence_text = f"{analysis.confidence_score:.2f}"
        if hasattr(analysis, 'estimated_complexity'):
            complexity_text = str(analysis.estimated_complexity)

        startup_type = ""
        if hasattr(analysis, 'startup_type'):
            startup_type = str(analysis.startup_type)

        lines.append(f"\n{i}. [{startup_type}] {idea_text}...")
        lines.append(f"   Problem: {problem_text}...")
        lines.append(f"   Confidence: {confidence_text} | Complexity: {complexity_text}")

    if len(analyses) > 5:
        lines.append(f"\n... and {len(analyses) - 5} more ideas (see output files for details)")

    return "\n".join(lines)
