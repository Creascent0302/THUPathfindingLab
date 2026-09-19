"""Standalone example. Other languages can implement the same JSONL protocol."""

from pathlab.worker import serve_plugin

if __name__ == "__main__":
    serve_plugin("student_template.algorithm:StudentAlgorithm")
