"""
Export Module
Handles exporting analysis results to various formats (CSV, JSON, Markdown).
Includes summary reporting functionality.
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    file_path: Optional[Path]
    record_count: int
    message: str
    error: Optional[str] = None


class CSVExporter:
    """Exports posts and analysis results to CSV format."""

    def __init__(self):
        """Initialize the CSV exporter."""
        self.fieldnames = [
            'title',
            'body',
            'upvotes',
            'url',
            'subreddit',
            'category',
            'category_score',
            'problem_score',
            'confidence_score',
            'quality_tier',
            'posted_date',
            'num_comments',
            'startup_idea',
            'startup_type',
            'core_problem_summary',
            'target_audience',
            'estimated_complexity',
            'potential_market_size',
            'model_used',
            'analysis_timestamp',
        ]

    def export(self, data: List[Dict[str, Any]], 
               filepath: str or Path = None,
               sort_by: str = 'confidence_score',
               ascending: bool = False) -> ExportResult:
        """
        Export data to CSV file.

        Args:
            data: List of post/analysis dictionaries
            filepath: Output file path (auto-generated if None)
            sort_by: Field to sort by
            ascending: Sort direction

        Returns:
            ExportResult with success status and details
        """
        if not data:
            return ExportResult(
                success=False,
                file_path=None,
                record_count=0,
                message="No data to export",
                error="Empty data list"
            )

        try:
            # Auto-generate filepath if not provided
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = Path(f"exports/reddit_analysis_{timestamp}.csv")

            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Sort data if requested
            if sort_by:
                sorted_data = sorted(data, key=lambda x: x.get(sort_by, 0), reverse=not ascending)
            else:
                sorted_data = data

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(sorted_data)

            logger.info(f"Exported {len(data)} records to {filepath}")

            return ExportResult(
                success=True,
                file_path=filepath,
                record_count=len(data),
                message=f"Successfully exported {len(data)} records to {filepath}"
            )

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return ExportResult(
                success=False,
                file_path=None,
                record_count=0,
                message="Export failed",
                error=str(e)
            )

    def export_with_metadata(self, data: List[Dict[str, Any]],
                              filepath: str or Path = None) -> ExportResult:
        """
        Export with additional metadata columns.
        
        Args:
            data: List of post/analysis dictionaries
            filepath: Output file path
            
        Returns:
            ExportResult with success status
        """
        if not data:
            return ExportResult(
                success=False,
                file_path=None,
                record_count=0,
                message="No data to export"
            )

        # Add metadata
        enriched_data = []
        for item in data:
            enriched = item.copy()
            enriched['export_date'] = datetime.now().isoformat()
            enriched_data.append(enriched)

        return self.export(enriched_data, filepath)


class JSONExporter:
    """Exports data to JSON format."""

    def __init__(self, indent: int = 2):
        """
        Initialize JSON exporter.
        
        Args:
            indent: JSON indentation spaces
        """
        self.indent = indent

    def export(self, data: Any, 
               filepath: str or Path = None,
               include_metadata: bool = True) -> ExportResult:
        """
        Export data to JSON file.

        Args:
            data: Data to export (list or dict)
            filepath: Output file path
            include_metadata: Add export metadata

        Returns:
            ExportResult with success status
        """
        try:
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = Path(f"exports/reddit_analysis_{timestamp}.json")

            filepath.parent.mkdir(parents=True, exist_ok=True)

            export_data = data

            if include_metadata:
                export_data = {
                    'export_metadata': {
                        'export_date': datetime.now().isoformat(),
                        'record_count': len(data) if isinstance(data, list) else 1,
                        'format': 'json',
                    },
                    'data': data
                }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=self.indent, ensure_ascii=False)

            record_count = len(data) if isinstance(data, list) else 1

            return ExportResult(
                success=True,
                file_path=filepath,
                record_count=record_count,
                message=f"Successfully exported {record_count} records to {filepath}"
            )

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return ExportResult(
                success=False,
                file_path=None,
                record_count=0,
                message="Export failed",
                error=str(e)
            )


class SummaryReporter:
    """Generates summary reports from analysis results."""

    def __init__(self):
        """Initialize the summary reporter."""
        pass

    def generate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from analysis data.

        Args:
            data: List of analyzed posts

        Returns:
            Dictionary with summary statistics
        """
        if not data:
            return {
                'total_posts': 0,
                'message': 'No data to summarize'
            }

        # Basic counts
        total = len(data)

        # Category distribution
        category_counts: Dict[str, int] = {}
        quality_counts: Dict[str, int] = {}
        subreddit_counts: Dict[str, int] = {}

        total_confidence = 0.0
        total_upvotes = 0

        for item in data:
            # Category
            cat = item.get('category', 'Uncategorized')
            category_counts[cat] = category_counts.get(cat, 0) + 1

            # Quality tier
            tier = item.get('quality_tier', 'Unknown')
            quality_counts[tier] = quality_counts.get(tier, 0) + 1

            # Subreddit
            sub = item.get('subreddit', 'Unknown')
            subreddit_counts[sub] = subreddit_counts.get(sub, 0) + 1

            # Aggregates
            total_confidence += item.get('confidence_score', 0)
            total_upvotes += item.get('upvotes', 0)

        # Sort for display
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_quality = sorted(quality_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_subreddits = sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            'total_posts': total,
            'average_confidence': round(total_confidence / total, 3) if total > 0 else 0,
            'total_upvotes': total_upvotes,
            'category_distribution': dict(sorted_categories),
            'quality_distribution': dict(sorted_quality),
            'subreddit_distribution': dict(sorted_subreddits),
            'generated_at': datetime.now().isoformat()
        }

    def print_summary(self, data: List[Dict[str, Any]], 
                      title: str = "ANALYSIS SUMMARY") -> str:
        """
        Generate and print a formatted summary report.

        Args:
            data: List of analyzed posts
            title: Report title

        Returns:
            Formatted summary string
        """
        summary = self.generate_summary(data)

        if summary.get('total_posts', 0) == 0:
            output = f"\n{'-' * 60}\n{title}\n{'-' * 60}\nNo posts analyzed.\n"
            print(output)
            return output

        output_lines = [
            "",
            "=" * 70,
            f"  {title}",
            "=" * 70,
            "",
            f"  Total Posts Analyzed: {summary['total_posts']}",
            f"  Average Confidence:   {summary['average_confidence']:.1%}",
            f"  Total Upvotes:        {summary['total_upvotes']}",
            "",
            "-" * 70,
            "  CATEGORY DISTRIBUTION",
            "-" * 70,
        ]

        for cat, count in summary['category_distribution'].items():
            pct = count / summary['total_posts'] * 100
            output_lines.append(f"  {cat}: {count} ({pct:.1f}%)")

        output_lines.extend([
            "",
            "-" * 70,
            "  QUALITY DISTRIBUTION",
            "-" * 70,
        ])

        for quality, count in summary['quality_distribution'].items():
            pct = count / summary['total_posts'] * 100
            output_lines.append(f"  {quality}: {count} ({pct:.1f}%)")

        output_lines.extend([
            "",
            "-" * 70,
            "  TOP SUBREDDITS",
            "-" * 70,
        ])

        for sub, count in list(summary['subreddit_distribution'].items())[:5]:
            pct = count / summary['total_posts'] * 100
            output_lines.append(f"  r/{sub}: {count} ({pct:.1f}%)")

        output_lines.extend([
            "",
            "-" * 70,
            "  TOP OPPORTUNITIES (by confidence)",
            "-" * 70,
        ])

        # Get top 5 by confidence
        sorted_by_conf = sorted(data, key=lambda x: x.get('confidence_score', 0), reverse=True)[:5]
        for i, item in enumerate(sorted_by_conf, 1):
            title_preview = item.get('title', 'No title')[:50]
            conf = item.get('confidence_score', 0)
            upvotes = item.get('upvotes', 0)
            output_lines.append(
                f"  {i}. [{conf:.0%}] [{upvotes} upvotes] {title_preview}..."
            )
            output_lines.append(f"     Category: {item.get('category', 'N/A')}")

        output_lines.extend([
            "",
            "=" * 70,
            f"  Generated: {summary['generated_at'][:19]}",
            "=" * 70,
            "",
        ])

        output = "\n".join(output_lines)
        print(output)
        return output

    def get_top_opportunities(self, data: List[Dict[str, Any]], 
                               limit: int = 10,
                               min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get the highest-confidence opportunities from analyzed posts.

        Args:
            data: List of analyzed posts
            limit: Maximum number to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of top opportunities sorted by confidence
        """
        filtered = [p for p in data if p.get('confidence_score', 0) >= min_confidence]
        sorted_posts = sorted(filtered, key=lambda x: x.get('confidence_score', 0), reverse=True)
        return sorted_posts[:limit]


class ExportManager:
    """
    Central manager for all export operations.
    Provides unified interface for CSV, JSON, and reporting.
    """

    def __init__(self, output_dir: str = "exports"):
        """
        Initialize export manager.

        Args:
            output_dir: Directory for export files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
        self.summary_reporter = SummaryReporter()

    def export_all(self, data: List[Dict[str, Any]]) -> Dict[str, ExportResult]:
        """
        Export data to all available formats.

        Args:
            data: Data to export

        Returns:
            Dictionary of ExportResult for each format
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        results = {
            'csv': self.csv_exporter.export(
                data, 
                self.output_dir / f"analysis_{timestamp}.csv"
            ),
            'json': self.json_exporter.export(
                data,
                self.output_dir / f"analysis_{timestamp}.json"
            ),
        }

        # Print summary
        summary_text = self.summary_reporter.print_summary(data)

        return results

    def export_custom(self, data: List[Dict[str, Any]],
                      format: str = 'csv',
                      filepath: str = None) -> ExportResult:
        """
        Export data to a specific format.

        Args:
            data: Data to export
            format: Export format ('csv', 'json')
            filepath: Custom filepath

        Returns:
            ExportResult
        """
        if format.lower() == 'csv':
            return self.csv_exporter.export(data, filepath)
        elif format.lower() == 'json':
            return self.json_exporter.export(data, filepath)
        else:
            return ExportResult(
                success=False,
                file_path=None,
                record_count=0,
                message=f"Unsupported format: {format}",
                error=f"Format '{format}' not supported. Use 'csv' or 'json'."
            )
